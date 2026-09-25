import pytest
from unittest.mock import patch, MagicMock
from backend.agent.access_guard import hard_rbac_check, AccessDecision
from backend.agent.agent_controller import _extract_intent_target, process_message
from backend.database import User

def test_hard_rbac_check():
    # Admin can do anything
    allowed, _ = hard_rbac_check("admin", "admin_manage")
    assert allowed is True
    
    # User cannot do admin manage
    allowed, reason = hard_rbac_check("user", "admin_manage")
    assert allowed is False
    assert "not allowed to use tool 'admin_manage'" in reason

    # Staff cannot do admin manage
    allowed, _ = hard_rbac_check("staff", "admin_manage")
    assert allowed is False

    # Staff can do staff_info
    allowed, _ = hard_rbac_check("staff", "get_staff_info")
    assert allowed is True

def test_extract_intent_target(db_session):
    # This function uses heuristics to find target
    user = db_session.query(User).filter_by(username="user_alice").first()
    
    intent = _extract_intent_target("who am i?", user.role, user.id, db_session)
    assert intent["resource"] == "own_profile"
    assert intent["owner_id"] == user.id

    intent2 = _extract_intent_target("tell me about user_bob", user.role, user.id, db_session)
    assert intent2["resource"] == "user_profile:user_bob"
    
    intent3 = _extract_intent_target("show me company policy", user.role, user.id, db_session)
    assert intent3["resource"] == "knowledge_base"

@patch('backend.agent.agent_controller.check_access')
@patch('backend.agent.agent_controller._get_gemini_client')
@patch('backend.agent.agent_controller._execute_tool')
def test_process_message(mock_execute_tool, mock_gemini, mock_check_access, db_session):
    # Setup mocks
    mock_check_access.return_value = AccessDecision(
        allowed=True,
        probability=0.9,
        sensitivity="low",
        sensitivity_score=0.1,
        recommended_tool="general_chat",
        tool_confidence=0.95,
        reason="Mocked allowed"
    )
    
    mock_execute_tool.return_value = {"message": "Mock tool success"}
    
    mock_gemini_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "Hello from mocked Gemini"
    mock_gemini_instance.models.generate_content.return_value = mock_gemini_response
    mock_gemini.return_value = mock_gemini_instance
    
    user = db_session.query(User).filter_by(username="user_alice").first()
    
    result = process_message(user, "hello!", db_session)
    
    assert result["response"] == "Hello from mocked Gemini"
    assert result["tool_used"] == "general_chat"
    assert result["access_decision"] == "ALLOWED: Mocked allowed"
    
    # Verify audit log was created
    from backend.database import AuditLog
    log = db_session.query(AuditLog).filter_by(user_id=user.id).first()
    assert log is not None
    assert log.action == "chat:general_chat"
    assert log.decision == "allowed"

@patch('backend.agent.agent_controller.check_access')
def test_process_message_denied(mock_check_access, db_session):
    mock_check_access.return_value = AccessDecision(
        allowed=False,
        probability=0.1,
        sensitivity="high",
        sensitivity_score=0.9,
        recommended_tool="get_user_info",
        tool_confidence=0.8,
        reason="Mocked denied"
    )
    
    user = db_session.query(User).filter_by(username="user_alice").first()
    
    with patch('backend.agent.agent_controller._get_gemini_client') as mock_gemini:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "You do not have access."
        mock_instance.models.generate_content.return_value = mock_response
        mock_gemini.return_value = mock_instance
        
        result = process_message(user, "show me admin data", db_session)
        
        assert result["response"] == "You do not have access."
        assert "DENIED (Jev): Mocked denied" in result["access_decision"]
