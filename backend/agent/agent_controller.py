"""
Agentic controller — the brain of the chatbot.

Orchestrates:
  1. Jev → decides which tool to use + access check
  2. Tool execution → retrieves data
  3. Gemini → generates natural-language response from tool output
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from google import genai
from sqlalchemy.orm import Session

from backend.agent.access_guard import check_access, hard_rbac_check, route_tool
from backend.agent.tool_registry import registry
from backend.agent.tools.admin_tool import (
    get_audit_logs,
    get_system_stats,
    list_all_users,
)
from backend.agent.tools.kb_tool import list_documents
from backend.agent.tools.rag_tool import rag_search
from backend.agent.tools.staff_tool import get_staff_info, list_all_staff
from backend.agent.tools.user_tool import get_user_info, list_users_for_staff
from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.database import AuditLog, ChatMessage, User

logger = logging.getLogger(__name__)

# ─── Gemini client ───────────────────────────────────────────────────────────

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


# ─── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligent assistant in a role-based access control system.
You help users, staff, and admins with their queries.

RULES:
- Always be helpful and professional.
- If tool results show access was denied, explain politely that the user doesn't have permission.
- Never reveal sensitive data that wasn't returned by the tools.
- When presenting user data, format it clearly.
- If RAG results are provided, synthesize them into a coherent answer and cite sources.
- If no tools were needed, just have a normal conversation.
- Keep responses concise but informative.

Your user's role is: {role}
Your user's name is: {name}
"""


# ─── Agent loop ──────────────────────────────────────────────────────────────


def _extract_intent_target(query: str, user_role: str, user_id: int, db: Session) -> dict:
    """
    Use heuristics to extract potential target info from a query.
    This runs *before* Jev and feeds into the access check.
    """
    query_lower = query.lower().strip()
    target = {"resource": "general", "owner_id": None, "owner_role": None}

    # 1. Check for self-profile / identity queries
    self_phrases = [
        "who am i", "who i am", "about me", "my info", "my profile", "my data",
        "my email", "my phone", "my details", "myself", "show me my", "what is my",
        "tell me about me", "tell me about myself", "who am i?"
    ]
    if any(p in query_lower for p in self_phrases):
        target["resource"] = "own_profile"
        target["owner_id"] = user_id
        target["owner_role"] = user_role
        return target

    # 2. Check if user mentions specific usernames or full names
    all_users = db.query(User).all()
    for u in all_users:
        if u.username.lower() in query_lower or u.full_name.lower() in query_lower:
            if u.id == user_id:
                target["resource"] = "own_profile"
                target["owner_id"] = user_id
                target["owner_role"] = user_role
            else:
                target["resource"] = f"user_profile:{u.username}"
                target["owner_id"] = u.id
                target["owner_role"] = u.role
            return target

    # 3. Check for keywords indicating resource type
    if any(w in query_lower for w in ["document", "knowledge", "policy", "search", "find"]):
        target["resource"] = "knowledge_base"
    elif any(w in query_lower for w in ["audit", "log", "system", "stats"]):
        target["resource"] = "admin_data"
        target["owner_role"] = "admin"
    elif any(w in query_lower for w in ["staff", "assigned"]):
        target["resource"] = "staff_data"
        target["owner_role"] = "staff"
    elif any(w in query_lower for w in ["product", "item", "catalog"]):
        target["resource"] = "product_data"
    elif any(w in query_lower for w in ["sale", "revenue", "sell", "order"]):
        target["resource"] = "sales_data"
    elif any(w in query_lower for w in ["cart", "buy", "checkout", "purchase", "add to"]):
        target["resource"] = "cart_data"
        target["owner_id"] = user_id
    elif any(w in query_lower for w in ["history", "past order", "delivered", "status"]):
        target["resource"] = "order_history"
        target["owner_id"] = user_id
    elif any(w in query_lower for w in ["return", "refund"]):
        target["resource"] = "order_return"
        target["owner_id"] = user_id
    elif any(w in query_lower for w in ["recommend", "next", "what should i buy"]):
        target["resource"] = "product_recommendations"
        target["owner_id"] = user_id

    return target


def _execute_tool(
    tool_name: str,
    user: User,
    query: str,
    db: Session,
) -> dict:
    """Execute a tool and return its result."""
    try:
        if tool_name == "rag_search":
            return rag_search(query=query, user_role=user.role, db=db)

        elif tool_name == "get_user_info":
            # Try to find a mentioned user
            target_user = None
            query_lower = query.lower()
            all_users = db.query(User).all()
            for u in all_users:
                if u.id != user.id and (
                    u.username.lower() in query_lower
                    or u.full_name.lower() in query_lower
                ):
                    target_user = u
                    break

            if target_user:
                return get_user_info(
                    requester_id=user.id,
                    requester_role=user.role,
                    db=db,
                    target_user_id=target_user.id,
                )
            else:
                # Default: own info
                return get_user_info(
                    requester_id=user.id,
                    requester_role=user.role,
                    db=db,
                )

        elif tool_name == "get_staff_info":
            # Check if asking about specific staff
            query_lower = query.lower()
            staff_members = db.query(User).filter(User.role == "staff").all()
            target_staff = None
            for s in staff_members:
                if s.username.lower() in query_lower or s.full_name.lower() in query_lower:
                    target_staff = s
                    break

            if target_staff:
                return get_staff_info(
                    requester_id=user.id,
                    requester_role=user.role,
                    db=db,
                    target_staff_id=target_staff.id,
                )
            elif user.role == "admin":
                return list_all_staff(db=db)
            else:
                return get_staff_info(
                    requester_id=user.id,
                    requester_role=user.role,
                    db=db,
                )

        elif tool_name == "admin_manage":
            query_lower = query.lower()
            if "audit" in query_lower or "log" in query_lower:
                return get_audit_logs(db=db)
            elif "stat" in query_lower:
                return get_system_stats(db=db)
            elif "assign" in query_lower and "who" not in query_lower and "which" not in query_lower:
                return {
                    "message": "To assign staff, use the admin panel or provide: user_id and staff_id."
                }
            else:
                return list_all_users(db=db)

        elif tool_name == "knowledge_base":
            return list_documents(user_role=user.role, db=db)

        elif tool_name == "ecommerce_products":
            from backend.agent.tools.ecommerce_tool import get_product_info
            return get_product_info(db=db)

        elif tool_name == "ecommerce_sales":
            from backend.agent.tools.ecommerce_tool import get_sales_data
            return get_sales_data(db=db)

        elif tool_name == "ecommerce_cart":
            from backend.agent.tools.ecommerce_tool import manage_cart, checkout_cart
            # Simple heuristic for cart
            if "checkout" in query.lower():
                return checkout_cart(user.id, db)
            elif "buy" in query.lower() or "add" in query.lower():
                # Extract product name very naively
                words = query.lower().split()
                # we pass the query to Jev or Gemini? We can pass action="add" and product_name
                # A real system would use a sub-LLM here to extract args, but we can do a naive extraction
                # or better, just pass the query as product_name and let the DB LIKE query handle it
                # For demo, if 'mouse' in query: product_name = 'mouse'
                product_name = None
                for w in ["laptop", "keyboard", "mouse", "monitor"]:
                    if w in query.lower():
                        product_name = w
                        break
                return manage_cart(user.id, "add", db, product_name=product_name)
            else:
                return manage_cart(user.id, "view", db)

        elif tool_name == "ecommerce_history":
            from backend.agent.tools.ecommerce_tool import view_order_history
            return view_order_history(user.id, db)

        elif tool_name == "ecommerce_returns":
            from backend.agent.tools.ecommerce_tool import process_return
            # Naive extraction of order_id
            order_id = -1
            for word in query.replace("#", " ").split():
                if word.isdigit():
                    order_id = int(word)
                    break
            if order_id == -1:
                return {"error": "Please specify the Order ID you want to return."}
            return process_return(user.id, order_id, db)

        elif tool_name == "ecommerce_recommendations":
            from backend.agent.tools.ecommerce_tool import recommend_products
            return recommend_products(user.id, db)

        elif tool_name == "general_chat":
            return {"message": "No specific tool needed. Respond conversationally."}

        else:
            return {"message": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error ({tool_name}): {e}")
        return {"error": str(e)}


def _generate_response(
    user_query: str,
    user: User,
    tool_name: str,
    tool_result: dict,
    access_decision_str: str,
    chat_history: list[dict],
) -> str:
    """Use Gemini to generate a natural-language response."""
    system = SYSTEM_PROMPT.format(role=user.role, name=user.full_name)

    # Build context messages
    messages = [{"role": "user", "parts": [{"text": system}]}]
    messages.append({"role": "model", "parts": [{"text": "Understood. I'll follow these rules."}]})

    # Add recent chat history (last 10 messages)
    for msg in chat_history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [{"text": msg["content"]}]})

    # Add tool context
    tool_context = (
        f"\n[TOOL USED: {tool_name}]\n"
        f"[ACCESS DECISION: {access_decision_str}]\n"
        f"[TOOL RESULT: {json.dumps(tool_result, default=str, indent=2)}]\n\n"
        f"User's question: {user_query}\n\n"
        "Based on the tool result above, provide a helpful response to the user. "
        "If access was denied, explain politely. If data was found, present it clearly."
    )
    messages.append({"role": "user", "parts": [{"text": tool_context}]})

    try:
        client = _get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=messages,
        )
        return response.text or "I apologize, but I couldn't generate a response."
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        # Improved Fallback: Provide a user-friendly message rather than raw JSON
        if tool_result.get("error"):
            return f"⚠️ **Error encountered**: {tool_result['error']}"
        
        fallback_msg = "⚠️ **AI Generation Unavailable**: The Google Gemini API is currently experiencing high demand or is unavailable. Here is the raw data I retrieved for you:\n\n"
        fallback_msg += f"```json\n{json.dumps(tool_result, default=str, indent=2)}\n```"
        return fallback_msg


# ─── Public API ──────────────────────────────────────────────────────────────


def process_message(
    user: User,
    message: str,
    db: Session,
) -> dict:
    """
    Main entry point.  Processes a user chat message through the agent pipeline:
      1. Extract intent and target from the message
      2. Use Jev for tool routing + access check
      3. Hard RBAC check
      4. Execute tool
      5. Generate response via Gemini
      6. Save to chat history and audit log
    """
    # Step 1: Extract intent
    intent = _extract_intent_target(message, user.role, user.id, db)

    # Step 2: Get available tools for this role
    available_tools = registry.tool_names_for_role(user.role)

    # Step 3: Jev access check + tool routing
    access = check_access(
        user_role=user.role,
        user_id=user.id,
        user_query=message,
        target_resource=intent["resource"],
        target_owner_role=intent.get("owner_role"),
        target_owner_id=intent.get("owner_id"),
        available_tools=available_tools,
    )

    tool_name = access.recommended_tool

    # Step 4: Hard RBAC override
    rbac_ok, rbac_reason = hard_rbac_check(user.role, tool_name)
    if not rbac_ok:
        access_decision_str = f"DENIED (hard RBAC): {rbac_reason}"
        tool_name = "general_chat"
        tool_result = {
            "access_denied": True,
            "message": rbac_reason,
        }
        # Short-circuit LLM to save API costs
        response_text = f"🛡️ **Access Denied**: You do not have permission to do this. (Reason: {rbac_reason})"
        
    elif not access.allowed:
        access_decision_str = f"DENIED (Jev): {access.reason}"
        tool_result = {
            "access_denied": True,
            "message": f"Access check failed: {access.reason}",
        }
        # Short-circuit LLM to save API costs
        response_text = "🛡️ **Access Denied**: Based on security policies, you are not authorized to access this information or perform this action."
        
    else:
        access_decision_str = f"ALLOWED: {access.reason}"
        # Step 5: Execute tool
        tool_result = _execute_tool(tool_name, user, message, db)

        # Step 6: Get chat history for context
        recent_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        chat_history = [
            {"role": m.role, "content": m.content} for m in reversed(recent_messages)
        ]

        # Step 7: Generate response via Gemini
        response_text = _generate_response(
            user_query=message,
            user=user,
            tool_name=tool_name,
            tool_result=tool_result,
            access_decision_str=access_decision_str,
            chat_history=chat_history,
        )

    # Step 8: Save messages to database
    user_msg = ChatMessage(
        user_id=user.id,
        role="user",
        content=message,
    )
    assistant_msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content=response_text,
        tool_used=tool_name,
        access_decision=access_decision_str,
    )
    db.add(user_msg)
    db.add(assistant_msg)

    # Step 9: Audit log
    audit = AuditLog(
        user_id=user.id,
        action=f"chat:{tool_name}",
        resource=intent["resource"],
        decision="allowed" if access.allowed and rbac_ok else "denied",
        jev_probability=f"{access.probability:.2f}",
        reason=access_decision_str,
    )
    db.add(audit)
    db.commit()

    return {
        "response": response_text,
        "tool_used": tool_name,
        "access_decision": access_decision_str,
        "sources": tool_result.get("sources", []),
    }
