#!/usr/bin/env python3
"""
Pydantic models for API requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.
    
    Session ID Flow:
    - First message: Omit session_id (or send null). Server will generate one and return it.
    - Subsequent messages: Include the session_id from the first response to maintain conversation context.
    """
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(
        None, 
        description="Session ID. If not provided, a new session will be created. "
                    "Use the returned session_id in subsequent requests to maintain conversation context."
    )
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls made during conversation")


class ToolInfo(BaseModel):
    """Information about an MCP tool."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters schema")


class ToolsResponse(BaseModel):
    """Response model for tools endpoint."""
    tools: List[ToolInfo] = Field(..., description="List of available tools")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")


class SessionInfo(BaseModel):
    """Information about a chat session."""
    session_id: str = Field(..., description="Session ID")
    message_count: int = Field(..., description="Number of messages in session")
    history: List[Dict[str, Any]] = Field(..., description="Conversation history")
    is_authenticated: bool = Field(False, description="Whether customer is authenticated")
    customer_info: Optional[Dict[str, Any]] = Field(None, description="Authenticated customer information")


class SuccessResponse(BaseModel):
    """Generic success response."""
    status: str = Field("success", description="Response status")
    message: str = Field(..., description="Response message")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")


class SessionsListResponse(BaseModel):
    """Response model for listing sessions."""
    sessions: List[Dict[str, Any]] = Field(..., description="List of sessions")
    count: int = Field(..., description="Total number of sessions")

