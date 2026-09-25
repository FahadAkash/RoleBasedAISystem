"""
Jev-powered access guard.

Uses TypeSafe's System One model (Jev) for fast, structured access-control
decisions.  Three kinds of judgment run in a single request:

  • Noul  — "Should this role be allowed to access this resource?"
  • Choice — "Which tool should handle this user request?"
  • Score  — "How sensitive is this data relative to the requester?"

Hard RBAC rules still enforce absolute boundaries (admin-only data);
Jev handles the *nuanced* layer — e.g. detecting when a query implicitly
tries to reach another user's data.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

from backend.config import JEV_MODEL, TYPESAFE_API_KEY

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    """Result of a Jev access-control evaluation."""

    allowed: bool
    probability: float  # Noul probability the access is appropriate
    sensitivity: str  # Score level: low / medium / high / critical
    sensitivity_score: float
    recommended_tool: str  # Choice pick for which tool to use
    tool_confidence: float
    reason: str


@dataclass
class ToolRoutingDecision:
    """Result of Jev deciding which tool to call."""

    tool_name: str
    confidence: float
    probabilities: dict[str, float]


def _build_jev_client() -> TypeSafeClient:
    """Build a synchronous TypeSafe client."""
    return TypeSafeClient(api_key=TYPESAFE_API_KEY, model=JEV_MODEL)


# ─── Access check ────────────────────────────────────────────────────────────

def check_access(
    user_role: str,
    user_id: int,
    user_query: str,
    target_resource: str,
    target_owner_role: Optional[str] = None,
    target_owner_id: Optional[int] = None,
    available_tools: Optional[list[str]] = None,
) -> AccessDecision:
    """
    Ask Jev whether *this* user should access *this* resource, which tool
    to use, and how sensitive the data is — all in one request.
    """
    if available_tools is None:
        available_tools = [
            "rag_search",
            "get_user_info",
            "get_staff_info",
            "admin_manage",
            "knowledge_base",
            "ecommerce_products",
            "ecommerce_sales",
            "ecommerce_cart",
            "ecommerce_history",
            "ecommerce_returns",
            "ecommerce_recommendations",
            "general_chat",
        ]

    # Recognize self-data / own-profile requests
    is_own_data = (
        target_resource == "own_profile"
        or (target_owner_id is not None and target_owner_id == user_id)
    )
    if is_own_data:
        target_owner_id = user_id
        target_owner_role = user_role

    state = {
        "requester": {
            "role": user_role,
            "user_id": user_id,
        },
        "query": user_query,
        "target_resource": target_resource,
        "target_owner": {
            "role": target_owner_role or "unknown",
            "user_id": target_owner_id,
        },
        "access_policy": {
            "admin": "Can access all resources belonging to any user, staff, or admin. Can view sales data.",
            "staff": "Can access own data and data of users assigned to them. Can view sales data. Cannot access other staff or admin data.",
            "user": "Can only access their own data. Cannot access other users, staff, admin, or sales data. ALL ROLES CAN VIEW PRODUCT DATA.",
        },
    }

    questions = {
        "access_allowed": Noul(
            instructions=(
                "Based on the access policy, should the requester with role "
                f"'{user_role}' (user_id={user_id}) be allowed to access the "
                f"target resource '{target_resource}'? The target belongs to a "
                f"'{target_owner_role or 'unknown'}' (user_id={target_owner_id}). "
                "Consider: admins see everything; staff see only their assigned users "
                "and themselves; users see only themselves. Self/own-profile requests are always allowed."
            ),
        ),
        "tool_selection": Choice(
            instructions=(
                "Which tool should handle this user request? Pick the most "
                "appropriate tool based on what the user is asking."
            ),
            criteria={
                tool: f"Use the {tool} tool" for tool in available_tools
            },
        ),
        "sensitivity": Score(
            instructions=(
                f"How sensitive is the requested data ('{target_resource}') "
                f"relative to the requester's role ('{user_role}')?"
            ),
            criteria=[
                "low — public or general knowledge, no access concern",
                "medium — personal data that the user may legitimately need",
                "high — data belonging to others, requires elevated privilege",
                "critical — admin-only system data or credentials",
            ],
        ),
    }

    try:
        with _build_jev_client() as client:
            result = client.system_one(state=state, questions=questions)

        access_prob = result.nouls["access_allowed"].noul
        tool_choice = result.choices["tool_selection"].choice
        tool_conf = result.choices["tool_selection"].confidence
        sens_score = result.scores["sensitivity"].score
        sens_levels = ["low", "medium", "high", "critical"]
        # Map the 0-1 score to the closest level
        sens_idx = min(int(sens_score * len(sens_levels)), len(sens_levels) - 1)
        sens_label = sens_levels[sens_idx]

        # Own data is always granted
        if is_own_data:
            allowed = True
            access_prob = max(access_prob, 1.0)
            if tool_choice not in available_tools:
                tool_choice = "get_user_info"
        else:
            allowed = access_prob >= 0.6  # Threshold: 60% probability

        reason = (
            f"Jev access_prob={access_prob:.2f}, "
            f"sensitivity={sens_label}({sens_score:.2f}), "
            f"tool={tool_choice}(conf={tool_conf:.2f})"
        )

        logger.info(f"Access decision: {reason}, allowed={allowed}")

        return AccessDecision(
            allowed=allowed,
            probability=access_prob,
            sensitivity=sens_label,
            sensitivity_score=sens_score,
            recommended_tool=tool_choice,
            tool_confidence=tool_conf,
            reason=reason,
        )

    except Exception as e:
        logger.error(f"Jev access check failed: {e}")
        # Fail-safe: deny if Jev is unreachable, except for own-data requests
        is_own = target_owner_id == user_id
        return AccessDecision(
            allowed=is_own,
            probability=1.0 if is_own else 0.0,
            sensitivity="unknown",
            sensitivity_score=0.0,
            recommended_tool="general_chat",
            tool_confidence=0.0,
            reason=f"Jev unavailable ({e}); fail-safe {'allowed (own data)' if is_own else 'denied'}",
        )


# ─── Tool routing ────────────────────────────────────────────────────────────

def route_tool(
    user_role: str,
    user_query: str,
    available_tools: list[str],
) -> ToolRoutingDecision:
    """
    Ask Jev which tool should handle a chat message, without the full
    access-check overhead.  Used inside the agentic loop.
    """
    state = {
        "user_role": user_role,
        "query": user_query,
        "available_tools": available_tools,
    }

    tool_descriptions = {
        "rag_search": "Search the knowledge base documents using RAG (retrieval-augmented generation) for factual answers from uploaded documents.",
        "get_user_info": "Look up user profile information (name, email, department, etc.) from the database.",
        "get_staff_info": "Look up staff member information and their assigned users.",
        "admin_manage": "Administrative actions: list all users, assign staff, update users, view audit logs.",
        "knowledge_base": "Browse or list available documents and knowledge base categories.",
        "ecommerce_products": "View the e-commerce product catalog. Use when asking about products, catalog, stock, or prices.",
        "ecommerce_sales": "View e-commerce sales data. Use when asking about revenue, orders, or top-selling products.",
        "ecommerce_cart": "Manage shopping cart (add items, view cart, checkout, buy).",
        "ecommerce_history": "View past order history and delivery status.",
        "ecommerce_returns": "Process a product return for a delivered order.",
        "ecommerce_recommendations": "Get product recommendations based on purchase history.",
        "general_chat": "General conversation, greetings, help, or questions not requiring any specific tool.",
    }

    questions = {
        "tool": Choice(
            instructions=(
                "The user with role '{}' sent this message: '{}'. "
                "Which tool should handle this request? Pick the single best tool."
            ).format(user_role, user_query),
            criteria={
                t: tool_descriptions.get(t, f"Use {t}")
                for t in available_tools
            },
        ),
    }

    try:
        with _build_jev_client() as client:
            result = client.system_one(state=state, questions=questions)

        choice_answer = result.choices["tool"]
        probabilities = {}
        if hasattr(choice_answer, "distribution") and choice_answer.distribution:
            probabilities = dict(choice_answer.distribution)

        return ToolRoutingDecision(
            tool_name=choice_answer.choice,
            confidence=choice_answer.confidence,
            probabilities=probabilities,
        )

    except Exception as e:
        logger.error(f"Jev tool routing failed: {e}")
        return ToolRoutingDecision(
            tool_name="general_chat",
            confidence=0.0,
            probabilities={},
        )


# ─── Hard RBAC layer (runs *before* Jev for absolute rules) ─────────────────

def hard_rbac_check(user_role: str, tool_name: str) -> tuple[bool, str]:
    """
    Absolute rules that override Jev.  Returns (allowed, reason).
    """
    blocked: dict[str, set[str]] = {
        "user": {"admin_manage", "get_staff_info", "ecommerce_sales"},
        "staff": {"admin_manage"},
    }
    denied_tools = blocked.get(user_role, set())
    if tool_name in denied_tools:
        return False, f"Role '{user_role}' is not allowed to use tool '{tool_name}'"
    return True, "OK"
