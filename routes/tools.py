#!/usr/bin/env python3
"""
Tools-related API routes.
"""

from fastapi import APIRouter, HTTPException

from mcp_client import get_mcp_client
from models import ToolInfo, ToolsResponse


router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("", response_model=ToolsResponse)
async def get_tools():
    """
    Get list of available MCP tools.
    """
    try:
        mcp = await get_mcp_client()
        
        tools = [
            ToolInfo(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                parameters=tool.get("inputSchema", {})
            )
            for tool in mcp.tools
        ]
        
        return ToolsResponse(tools=tools)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tools: {str(e)}")

