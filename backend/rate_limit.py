import time
from collections import defaultdict
from fastapi import HTTPException, Depends
from backend.auth import get_current_user
from backend.database import User

# user_id -> list of timestamps
_request_history = defaultdict(list)

# Configuration: max requests per minute
MAX_REQUESTS_PER_MINUTE = 15

def rate_limit_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency that enforces a rate limit of requests per minute per user.
    Uses a simple sliding window algorithm in memory.
    """
    now = time.time()
    user_id = current_user.id
    
    # Filter out timestamps older than 60 seconds
    _request_history[user_id] = [t for t in _request_history[user_id] if now - t < 60]
    
    if len(_request_history[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {MAX_REQUESTS_PER_MINUTE} requests per minute allowed to protect API credits."
        )
        
    # Record this request
    _request_history[user_id].append(now)
    
    return current_user
