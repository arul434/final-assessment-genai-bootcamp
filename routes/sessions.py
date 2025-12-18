#!/usr/bin/env python3
"""
Session management API routes.
"""

import uuid
from fastapi import APIRouter, HTTPException

from chat_util import reset_session, delete_session, get_all_sessions
from models import SessionInfo, SuccessResponse, SessionsListResponse


router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/session/new", response_model=SuccessResponse)
async def create_new_session():
    """
    Create a new session ID without sending a message.
    Useful if you want to get a session ID upfront before starting the chat.
    
    Returns:
        Session ID that can be used in subsequent chat requests.
    """
    session_id = str(uuid.uuid4())
    return SuccessResponse(
        message="New session created",
        session_id=session_id
    )


@router.post("/reset/{session_id}", response_model=SuccessResponse)
async def reset_chat_session(session_id: str):
    """
    Reset a chat session (clear conversation history).
    The session_id remains valid but the conversation history is cleared.
    """
    try:
        reset_session(session_id)
        return SuccessResponse(
            message=f"Session {session_id} reset",
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting session: {str(e)}")


@router.delete("/reset/{session_id}", response_model=SuccessResponse)
async def delete_chat_session(session_id: str):
    """
    Delete a chat session completely.
    The session_id will no longer be valid after deletion.
    """
    try:
        delete_session(session_id)
        return SuccessResponse(
            message=f"Session {session_id} deleted",
            session_id=session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str):
    """
    Get information about a chat session (history, message count, etc.).
    Useful for debugging or displaying conversation history.
    """
    try:
        sessions = get_all_sessions()
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        session = sessions[session_id]
        history = session.get_history()
        
        return SessionInfo(
            session_id=session_id,
            message_count=len(history),
            history=history
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting session info: {str(e)}")


@router.get("/sessions", response_model=SessionsListResponse)
async def list_sessions():
    """
    List all active chat sessions (useful for debugging/admin).
    Returns summary information about each session.
    """
    try:
        all_sessions = get_all_sessions()
        sessions = []
        for session_id, session in all_sessions.items():
            history = session.get_history()
            sessions.append({
                "session_id": session_id,
                "message_count": len(history),
                "last_message": history[-1] if history else None
            })
        
        return SessionsListResponse(sessions=sessions, count=len(sessions))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")
