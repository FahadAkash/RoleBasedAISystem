import asyncio
from sqlalchemy.orm import Session
from backend.database import SessionLocal, User
from backend.agent.agent_controller import process_message

def run_test():
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username="user_alice").first()
        if not user:
            print("user_alice not found!")
            return
            
        queries = [
            "I want to buy the Quantum Laptop",
            "Checkout my cart",
            "What should I buy next?",
            "I want to return order 1",
            "I want to return order 2",
            "what is my order history?"
        ]
        
        for q in queries:
            print(f"\n=============================================")
            print(f"User: {user.username} | Role: {user.role}")
            print(f"Query: {q}")
            
            result = process_message(user, q, db)
            
            print(f"\nTool Used: {result.get('tool_used')}")
            print(f"Access Decision: {result.get('access_decision')}")
            print(f"Response:\n{result.get('response')}")
        
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
