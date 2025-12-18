#!/usr/bin/env python3
"""
Chat-related API routes.
"""

import json
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from chat_util import get_chat_session
from models import ChatRequest, ChatResponse
from config import settings


router = APIRouter(prefix="/api/chat", tags=["chat"])


def _create_stream_response(session, user_message: str, session_id: str):
    """Helper to create streaming response."""
    async def generate_stream():
        async for chunk in session.chat_stream(
            user_message=user_message,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        ):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - send a message and get a response.
    Supports both streaming and non-streaming modes.
    
    Session Management:
    - First message: Don't send session_id. Server generates one and returns it.
    - Subsequent messages: Include the session_id to continue the conversation.
    - Each session maintains its own conversation history.
    
    Example Flow:
    1. POST {"message": "Hello"} 
       → Returns {"response": "Hi!", "session_id": "abc-123"}
    2. POST {"message": "Show monitors", "session_id": "abc-123"}
       → Returns response with conversation context maintained
    """
    try:
        # Generate new session ID if not provided (first message)
        session_id = request.session_id or str(uuid.uuid4())
        session = await get_chat_session(session_id=session_id)
        
        if request.stream:
            return _create_stream_response(session, request.message, session_id)
        
        # Non-streaming response
        response_text = await session.chat(
            user_message=request.message,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            tool_calls=None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@router.get("/stream")
async def chat_stream(message: str, session_id: Optional[str] = None):
    """
    Streaming chat endpoint (alternative to POST with stream=true).
    Uses query parameters for easier integration.
    """
    try:
        session_id = session_id or str(uuid.uuid4())
        session = await get_chat_session(session_id=session_id)
        return _create_stream_response(session, message, session_id)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error streaming chat: {str(e)}")

