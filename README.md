# Role-Based AI System 🛡️🤖

Welcome to the **Role-Based AI System**, a next-generation agentic chatbot that intelligently combines natural language processing with **strict, deterministic access control** and fully functional **e-commerce workflows**.

## 🌟 Why is this advanced compared to other chatbots?

Most LLM-based chatbots suffer from severe security flaws (like Prompt Injection) when connected to internal databases. They rely on "soft prompts" (e.g., *"Don't tell the user the revenue if they aren't admin"*) which are easily bypassed by clever users.

**This project solves that by completely separating the brain from the security guard:**
1. **TypeSafe Jev (The Guard):** Before the LLM even sees the user's request, Jev (a deterministic categorization engine) analyzes the user's intent and evaluates it against strict Role-Based Access Control (RBAC) rules.
2. **Short-Circuiting:** If a user asks for something they aren't allowed to see (e.g., a standard user asking for total company revenue), the system **short-circuits**, instantly denying access without ever calling the LLM. This saves API costs and makes prompt injection impossible.
3. **Action Execution:** If approved, a local Python tool fetches the exact SQL data.
4. **Google Gemini (The Speaker):** Finally, Gemini is given the raw, sanitized SQL data and asked to format it into a friendly response.

## 🚀 Key Features

*   **Role-Based Access Control (RBAC):** Three distinct roles (`admin`, `staff`, `user`) with strict data isolation. Users can only see their own carts, staff can see assigned users, and admins see everything.
*   **Fully Interactive E-Commerce AI:** 
    *   Say *"Add the Quantum Laptop to my cart and checkout"* and the AI performs the SQL transactions.
    *   Say *"Has my order been delivered?"* and the AI checks the delivery dates.
    *   Say *"I want to return my mouse"* and the AI enforces a strict mathematically-checked **10-day return policy**.
    *   Say *"What should I buy next?"* and the AI generates recommendations based on purchase history.
*   **Cost-Optimized:** Includes a sliding-window rate limiter (max 15 requests/minute) and LLM short-circuiting on denied queries to prevent API credit burning.
*   **Knowledge Base (RAG):** Uses `sentence-transformers` and ChromaDB for instant retrieval of company policies and guidelines.

## 🛠️ Tech Stack

*   **Backend:** FastAPI (Python), SQLAlchemy (SQLite)
*   **Frontend:** Streamlit (WebSockets)
*   **AI / ML:** Google Gemini 2.5 Flash, TypeSafe Jev
*   **Vector DB:** ChromaDB

## 📦 How to Run Locally

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Set API Keys:**
   Create a `.env` file or export `GEMINI_API_KEY` and `TYPESAFE_API_KEY`.
3. **Run the Backend:**
   ```bash
   python -m uvicorn backend.main:app --reload --port 8000
   ```
4. **Run the Frontend (New Terminal):**
   ```bash
   python -m streamlit run frontend/app.py --server.port 8501
   ```
5. **Login:** Use credentials like `admin` (pass: `admin`), `staff_charlie` (pass: `pass`), or `user_alice` (pass: `pass`).

## ☁️ AWS Deployment (Free Tier)
We have included a `deploy_aws_ec2.sh` script! Simply spin up an Ubuntu `t2.micro` instance on AWS EC2, open ports `8000` and `8501`, clone this repo, and run `./deploy_aws_ec2.sh` to automatically install dependencies and set up 24/7 background services.
