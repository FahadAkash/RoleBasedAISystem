"""
Streamlit frontend for the Role-Based AI Chatbot.

A rich chat interface with login, role-based views, and admin dashboard.
"""

import json
import time

import httpx
import streamlit as st

# ─── Config ──────────────────────────────────────────────────────────────────

BACKEND_URL = "http://127.0.0.1:8000"

# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Chatbot — Role-Based Access",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
    /* ── Global ────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ── Sidebar ───────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 50%, #0f0f23 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e0e0ff;
    }

    /* ── Chat message styling ──────────────────────────────────── */
    .user-msg {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        margin: 8px 0;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
    }
    .assistant-msg {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e0e0ff;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        margin: 8px 0;
        max-width: 80%;
        border: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    }

    /* ── Badge styling ─────────────────────────────────────────── */
    .role-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .role-admin { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; }
    .role-staff { background: linear-gradient(135deg, #feca57, #ff9f43); color: #1a1a2e; }
    .role-user  { background: linear-gradient(135deg, #48dbfb, #0abde3); color: #1a1a2e; }

    /* ── Tool badge ────────────────────────────────────────────── */
    .tool-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.7em;
        background: rgba(102, 126, 234, 0.2);
        color: #667eea;
        border: 1px solid rgba(102, 126, 234, 0.3);
        margin-top: 4px;
    }

    /* ── Cards ──────────────────────────────────────────────────── */
    .stat-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    .stat-number {
        font-size: 2em;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        font-size: 0.85em;
        color: #888;
        margin-top: 4px;
    }

    /* ── Header ────────────────────────────────────────────────── */
    .main-header {
        text-align: center;
        padding: 20px 0;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2em;
        font-weight: 700;
    }

    /* ── Login card ────────────────────────────────────────────── */
    .login-container {
        max-width: 400px;
        margin: 60px auto;
        padding: 40px;
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 16px;
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
</style>
""",
    unsafe_allow_html=True,
)


# ─── Session state defaults ──────────────────────────────────────────────────


def init_session():
    defaults = {
        "authenticated": False,
        "token": None,
        "username": None,
        "role": None,
        "user_id": None,
        "messages": [],
        "page": "chat",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()


# ─── API helpers ─────────────────────────────────────────────────────────────


def api_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_post(endpoint: str, data: dict = None, timeout: float = 60.0):
    try:
        resp = httpx.post(
            f"{BACKEND_URL}{endpoint}",
            json=data,
            headers=api_headers(),
            timeout=timeout,
        )
        return resp
    except httpx.ConnectError:
        st.error("❌ Cannot connect to backend. Is the FastAPI server running?")
        return None
    except httpx.ReadTimeout:
        st.error("⏳ Request timed out. The AI is taking too long to respond.")
        return None


def api_get(endpoint: str, params: dict = None):
    try:
        resp = httpx.get(
            f"{BACKEND_URL}{endpoint}",
            headers=api_headers(),
            params=params,
            timeout=30.0,
        )
        return resp
    except httpx.ConnectError:
        st.error("❌ Cannot connect to backend. Is the FastAPI server running?")
        return None


def safe_json(resp, default=None):
    if resp is None:
        return default
    try:
        return resp.json()
    except Exception:
        if default is None:
            return {}
        return default


# ─── Login page ──────────────────────────────────────────────────────────────


def render_login():
    st.markdown(
        '<div class="main-header"><h1>🤖 AI Chatbot</h1>'
        "<p>Role-Based Access Control System</p></div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### 🔐 Sign In")

        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")

        if st.button("Sign In", type="primary", use_container_width=True):
            if not username or not password:
                st.error("Please enter both username and password.")
                return

            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/auth/login",
                    json={"username": username, "password": password},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        st.session_state.authenticated = True
                        st.session_state.token = data["access_token"]
                        st.session_state.username = data["username"]
                        st.session_state.role = data["role"]
                        st.session_state.user_id = data["user_id"]
                        st.session_state.messages = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to parse response from server: {e}")
                else:
                    try:
                        error = resp.json().get("detail", "Login failed")
                    except Exception:
                        error = f"Login failed (HTTP {resp.status_code}): {resp.text}"
                    st.error(f"❌ {error}")
            except httpx.ConnectError:
                st.error("❌ Cannot connect to backend. Start the FastAPI server first!")
            except Exception as e:
                st.error(f"❌ Unexpected error during login: {e}")

        st.markdown("---")
        st.markdown("##### 🧪 Demo Accounts")
        demo_data = [
            ("admin", "admin123", "admin"),
            ("staff_sarah", "staff123", "staff"),
            ("staff_mike", "staff123", "staff"),
            ("user_alice", "user123", "user"),
            ("user_bob", "user123", "user"),
            ("user_carol", "user123", "user"),
        ]
        for uname, pwd, role in demo_data:
            role_colors = {"admin": "🔴", "staff": "🟡", "user": "🔵"}
            st.caption(f"{role_colors[role]} **{uname}** / `{pwd}` ({role})")


# ─── Sidebar ─────────────────────────────────────────────────────────────────


def render_sidebar():
    with st.sidebar:
        # User info
        role = st.session_state.role
        role_class = f"role-{role}"
        st.markdown(
            f"### 👤 {st.session_state.username}",
        )
        st.markdown(
            f'<span class="role-badge {role_class}">{role}</span>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # Navigation
        st.markdown("### 📋 Navigation")

        if st.button("💬 Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

        if role in ("admin", "staff"):
            if st.button("📄 Documents", use_container_width=True):
                st.session_state.page = "documents"
                st.rerun()

        if role == "admin":
            if st.button("👥 User Management", use_container_width=True):
                st.session_state.page = "admin_users"
                st.rerun()
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "admin_dashboard"
                st.rerun()
            if st.button("📝 Audit Logs", use_container_width=True):
                st.session_state.page = "audit_logs"
                st.rerun()

        st.markdown("---")

        # Actions
        if st.button("🗑️ Clear Chat", use_container_width=True):
            resp = httpx.delete(
                f"{BACKEND_URL}/chat/history",
                headers=api_headers(),
                timeout=10.0,
            )
            st.session_state.messages = []
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown("---")
        st.markdown("##### ⚙️ System Info")
        st.caption("🧠 **AI**: Google Gemini")
        st.caption("🛡️ **Access**: TypeSafe Jev")
        st.caption("📚 **RAG**: ChromaDB + MiniLM")
        st.caption("💾 **DB**: SQLite")


# ─── Chat page ───────────────────────────────────────────────────────────────


def render_chat():
    st.markdown(
        '<div class="main-header"><h1>💬 AI Assistant</h1></div>',
        unsafe_allow_html=True,
    )

    # Load history if empty
    if not st.session_state.messages:
        resp = api_get("/chat/history")
        if resp and resp.status_code == 200:
            history = safe_json(resp, [])
            st.session_state.messages = [
                {"role": m["role"], "content": m["content"], "tool_used": m.get("tool_used")}
                for m in history
                if isinstance(m, dict)
            ]

    # Display messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            with st.chat_message("user" if role == "user" else "assistant"):
                st.markdown(msg["content"])
                if msg.get("tool_used") and msg["tool_used"] != "general_chat":
                    st.markdown(
                        f'<span class="tool-badge">🔧 {msg["tool_used"]}</span>',
                        unsafe_allow_html=True,
                    )

    # Input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                resp = api_post("/chat/", {"message": prompt})

            if resp and resp.status_code == 200:
                data = safe_json(resp, {})
                response = data.get("response", "No response generated.")
                tool_used = data.get("tool_used", "")
                access = data.get("access_decision", "")

                st.markdown(response)

                if tool_used and tool_used != "general_chat":
                    st.markdown(
                        f'<span class="tool-badge">🔧 {tool_used}</span>',
                        unsafe_allow_html=True,
                    )

                if access:
                    with st.expander("🛡️ Access Decision"):
                        st.code(access)

                if data.get("sources"):
                    with st.expander("📚 Sources"):
                        for src in data["sources"]:
                            st.markdown(f"• {src}")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response,
                        "tool_used": tool_used,
                    }
                )
            elif resp:
                error = safe_json(resp, {}).get("detail", f"Error HTTP {resp.status_code}")
                st.error(f"❌ {error}")
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Error: {error}"}
                )


# ─── Documents page ──────────────────────────────────────────────────────────


def render_documents():
    st.markdown("### 📄 Knowledge Base Documents")

    # Upload form
    with st.expander("➕ Upload New Document", expanded=False):
        title = st.text_input("Title")
        content = st.text_area("Content", height=200)
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", ["general", "policy", "technical"])
        with col2:
            access_level = st.selectbox("Access Level", ["all", "staff", "admin"])

        if st.button("Upload Document", type="primary"):
            if title and content:
                resp = api_post(
                    "/admin/documents",
                    {
                        "title": title,
                        "content": content,
                        "category": category,
                        "access_level": access_level,
                    },
                )
                if resp and resp.status_code == 200:
                    st.success(resp.json().get("message", "Document uploaded!"))
                else:
                    st.error("Failed to upload document.")
            else:
                st.warning("Please provide both title and content.")

    # List documents
    resp = api_get("/admin/documents")
    if resp and resp.status_code == 200:
        data = resp.json()
        docs = data.get("documents", [])
        if docs:
            for doc in docs:
                access_colors = {"all": "🟢", "staff": "🟡", "admin": "🔴"}
                icon = access_colors.get(doc["access_level"], "⚪")
                st.markdown(
                    f"**{icon} {doc['title']}** — "
                    f"Category: `{doc['category']}` | "
                    f"Access: `{doc['access_level']}`"
                )
        else:
            st.info("No documents found.")


# ─── Admin: User management ─────────────────────────────────────────────────


def render_admin_users():
    st.markdown("### 👥 User Management")

    resp = api_get("/admin/users")
    if resp and resp.status_code == 200:
        users = resp.json()

        # Display user cards
        for user in users:
            role = user.get("role", "user")
            role_emoji = {"admin": "🔴", "staff": "🟡", "user": "🔵"}.get(role, "⚪")
            active = "✅" if user.get("is_active") else "❌"

            with st.expander(
                f"{role_emoji} {user['full_name']} (@{user['username']}) — {role.upper()}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Email:** {user.get('email', 'N/A')}")
                    st.markdown(f"**Department:** {user.get('department', 'N/A')}")
                with col2:
                    st.markdown(f"**Active:** {active}")
                    st.markdown(
                        f"**Assigned Staff ID:** {user.get('assigned_staff_id', 'None')}"
                    )


# ─── Admin: Dashboard ────────────────────────────────────────────────────────


def render_admin_dashboard():
    st.markdown("### 📊 System Dashboard")

    resp = api_get("/admin/stats")
    if resp and resp.status_code == 200:
        stats = resp.json()

        cols = st.columns(4)
        stat_items = [
            ("Total Users", stats.get("total_users", 0), "👥"),
            ("Active Users", stats.get("active_users", 0), "✅"),
            ("Staff Members", stats.get("staff", 0), "👔"),
            ("Denied Attempts", stats.get("denied_access_attempts", 0), "🚫"),
        ]

        for col, (label, value, emoji) in zip(cols, stat_items):
            with col:
                st.markdown(
                    f"""
                    <div class="stat-card">
                        <div>{emoji}</div>
                        <div class="stat-number">{value}</div>
                        <div class="stat-label">{label}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # Role distribution
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Role Distribution")
            role_data = {
                "Admins": stats.get("admins", 0),
                "Staff": stats.get("staff", 0),
                "Users": stats.get("regular_users", 0),
            }
            st.bar_chart(role_data)

        with col2:
            st.markdown("#### Security Summary")
            total_audits = stats.get("total_audit_entries", 0)
            denied = stats.get("denied_access_attempts", 0)
            allowed = total_audits - denied
            st.metric("Total Access Decisions", total_audits)
            st.metric("Allowed", allowed)
            st.metric("Denied", denied)


# ─── Admin: Audit logs ──────────────────────────────────────────────────────


def render_audit_logs():
    st.markdown("### 📝 Audit Logs")

    resp = api_get("/admin/audit-logs", {"limit": 100})
    if resp and resp.status_code == 200:
        data = resp.json()
        logs = data.get("logs", [])

        if logs:
            for log in logs:
                decision = log.get("decision", "unknown")
                icon = "✅" if decision == "allowed" else "🚫"
                st.markdown(
                    f"{icon} **User #{log['user_id']}** | "
                    f"Action: `{log['action']}` | "
                    f"Resource: `{log['resource']}` | "
                    f"Decision: **{decision}** | "
                    f"Jev: `{log.get('jev_probability', 'N/A')}`"
                )
                if log.get("reason"):
                    st.caption(f"   ↳ {log['reason']}")
        else:
            st.info("No audit log entries yet.")


# ─── Main routing ────────────────────────────────────────────────────────────


def main():
    if not st.session_state.authenticated:
        render_login()
    else:
        render_sidebar()

        page = st.session_state.page
        if page == "chat":
            render_chat()
        elif page == "documents":
            render_documents()
        elif page == "admin_users":
            render_admin_users()
        elif page == "admin_dashboard":
            render_admin_dashboard()
        elif page == "audit_logs":
            render_audit_logs()
        else:
            render_chat()


if __name__ == "__main__":
    main()
