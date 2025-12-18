#!/usr/bin/env python3
"""
MCP Client for connecting to MCP server over HTTP/SSE.
"""

import os
import json
import httpx
import requests
from typing import Optional, Dict, Any, List
import uuid
from sseclient import SSEClient


class MCPClient:
    """Client for communicating with MCP server over HTTP/SSE."""
    
    def __init__(self, server_url: str):
        """
        Initialize MCP client.
        
        Args:
            server_url: Base URL of the MCP server
        """
        self.server_url = server_url.rstrip('/')
        self.tools: List[Dict[str, Any]] = []
        self.client = httpx.AsyncClient(timeout=60.0)
        self._initialized = False
    
    async def _send_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a JSON-RPC request via SSE stream.
        
        Args:
            method: JSON-RPC method name
            params: Method parameters
            
        Returns:
            Response from the server
        """
        import asyncio
        
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Use requests library for SSE (sseclient works with requests)
        def _sync_request():
            headers = {
                "Accept": "text/event-stream, application/json",
                "Content-Type": "application/json",
                "Cache-Control": "no-cache"
            }
            response = requests.post(
                self.server_url,
                json=request,
                headers=headers,
                stream=True,
                timeout=30
            )
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            
            # Check if response is JSON or SSE
            if 'application/json' in content_type:
                # Direct JSON response
                data = response.json()
                if data.get("id") == request_id:
                    if "error" in data:
                        raise Exception(f"MCP Error: {data['error']}")
                    return data.get("result")
                elif "error" in data:
                    raise Exception(f"MCP Server Error: {data['error']}")
                else:
                    raise Exception(f"Unexpected response format: {data}")
            elif 'text/event-stream' in content_type:
                # SSE stream response
                client = SSEClient(response)
                result = None
                for event in client.events():
                    if event.data:
                        try:
                            data = json.loads(event.data)
                            # Check if this is the response for our request
                            if data.get("id") == request_id:
                                if "error" in data:
                                    raise Exception(f"MCP Error: {data['error']}")
                                result = data.get("result")
                                break
                            # Also check if it's a response without matching ID (might be server error)
                            elif "error" in data and data.get("id") == "server-error":
                                raise Exception(f"MCP Server Error: {data['error']}")
                        except json.JSONDecodeError:
                            continue
                
                if result is None:
                    raise Exception(f"No response received for method {method}")
                
                return result
            else:
                raise Exception(f"Unexpected Content-Type: {content_type}")
        
        # Run sync request in executor to make it async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_request)
    
    async def initialize(self):
        """Initialize connection and fetch available tools."""
        if self._initialized:
            return
        
        try:
            # List available tools from MCP server using JSON-RPC
            result = await self._send_jsonrpc_request("tools/list")
            
            if isinstance(result, dict) and 'tools' in result:
                self.tools = result['tools']
            elif isinstance(result, list):
                self.tools = result
            else:
                self.tools = []
            
            self._initialized = True
        except Exception as e:
            print(f"Error initializing MCP client: {e}")
            raise
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        try:
            result = await self._send_jsonrpc_request(
                "tools/call",
                params={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
            return result
        except Exception as e:
            raise Exception(f"Error calling tool {tool_name}: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, 'client'):
            # Note: This won't work for async cleanup, but helps with sync cleanup
            pass


# Global client instance
_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """
    Get or create MCP client instance.
    
    Returns:
        Initialized MCPClient instance
    """
    global _client
    
    if _client is None:
        server_url = os.getenv(
            'MCP_SERVER_URL',
            'https://vipfapwm3x.us-east-1.awsapprunner.com/mcp'
        )
        _client = MCPClient(server_url)
        await _client.initialize()
    
    return _client

