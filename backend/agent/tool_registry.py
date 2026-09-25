"""Tool registry — defines all available tools and their metadata."""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolDefinition:
    """Describes a tool available to the agent."""

    name: str
    description: str
    required_role: str  # Minimum role: "user" | "staff" | "admin"
    function: Optional[Callable] = None
    parameters: dict[str, Any] = field(default_factory=dict)


# Role hierarchy for comparison
ROLE_HIERARCHY = {"user": 0, "staff": 1, "admin": 2}


class ToolRegistry:
    """Central registry of all agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_for_role(self, role: str) -> list[ToolDefinition]:
        """Return tools accessible to the given role."""
        user_level = ROLE_HIERARCHY.get(role, 0)
        return [
            t
            for t in self._tools.values()
            if ROLE_HIERARCHY.get(t.required_role, 0) <= user_level
        ]

    def tool_names_for_role(self, role: str) -> list[str]:
        return [t.name for t in self.list_for_role(role)]

    @property
    def all_tools(self) -> dict[str, ToolDefinition]:
        return dict(self._tools)


# ─── Global registry instance ────────────────────────────────────────────────
registry = ToolRegistry()


def _register_all_tools() -> None:
    """Register all tools. Called once at import."""

    registry.register(
        ToolDefinition(
            name="rag_search",
            description=(
                "Search the knowledge base using RAG (retrieval-augmented generation). "
                "Use this when the user asks factual questions that may be answered by "
                "uploaded documents, policies, or manuals."
            ),
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="get_user_info",
            description=(
                "Look up a user's profile information (name, email, department, phone). "
                "Users can look up their own info. Staff can look up their assigned "
                "users. Admins can look up anyone."
            ),
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="get_staff_info",
            description=(
                "Look up staff member information and see which users are assigned to "
                "them. Only staff (own info) and admins can use this."
            ),
            required_role="staff",
        )
    )
    registry.register(
        ToolDefinition(
            name="admin_manage",
            description=(
                "Administrative operations: list all users, assign staff to users, "
                "update user profiles, view audit logs. Admin only."
            ),
            required_role="admin",
        )
    )
    registry.register(
        ToolDefinition(
            name="knowledge_base",
            description=(
                "Browse or list available documents and categories in the knowledge "
                "base. Use when the user wants to know what documents are available."
            ),
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="general_chat",
            description=(
                "General conversation, greetings, help requests, or any question "
                "that doesn't require a specific tool. Also used as a fallback."
            ),
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_products",
            description=(
                "View the e-commerce product catalog. Use this when the user asks "
                "about products, prices, stock, or descriptions."
            ),
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_sales",
            description=(
                "View e-commerce sales data, total revenue, and top-selling products. "
                "Only staff and admins can use this."
            ),
            required_role="staff",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_cart",
            description="Manage shopping cart (add items, view cart, or checkout).",
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_history",
            description="View past order history and delivery status.",
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_returns",
            description="Process a product return for a delivered order.",
            required_role="user",
        )
    )
    registry.register(
        ToolDefinition(
            name="ecommerce_recommendations",
            description="Get product recommendations based on purchase history.",
            required_role="user",
        )
    )

_register_all_tools()
