#!/usr/bin/env python3
"""
Unit tests for MCPClient.
"""

import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from src.core.mcp_client import MCPClient, get_mcp_client


class TestMCPClient:
    """Test suite for MCPClient class."""
    
    @pytest.fixture
    def server_url(self):
        """Fixture providing a test server URL."""
        return "https://test-mcp-server.com/mcp"
    
    @pytest.fixture
    def mcp_client(self, server_url):
        """Fixture providing an MCPClient instance."""
        return MCPClient(server_url)
    
    def test_init(self, server_url):
        """Test MCPClient initialization."""
        client = MCPClient(server_url)
        
        assert client.server_url == server_url.rstrip('/')
        assert client.tools == []
        assert client._initialized is False
    
    def test_init_strips_trailing_slash(self):
        """Test that initialization strips trailing slash from URL."""
        client = MCPClient("https://test.com/mcp/")
        assert client.server_url == "https://test.com/mcp"
    
    @pytest.mark.asyncio
    async def test_send_jsonrpc_request_json_response(self, mcp_client):
        """Test _send_jsonrpc_request with JSON response."""
        request_id = "test-request-id"
        mock_result = {"tools": [{"name": "test_tool"}]}
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": mock_result
        }
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: request_id)):
                result = await mcp_client._send_jsonrpc_request("tools/list")
                
                assert result == mock_result
                mock_response.raise_for_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_jsonrpc_request_sse_response(self, mcp_client):
        """Test _send_jsonrpc_request with SSE stream response."""
        request_id = "test-request-id"
        mock_result = {"tools": [{"name": "test_tool"}]}
        
        # Mock SSE events
        mock_event1 = MagicMock()
        mock_event1.data = json.dumps({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": mock_result
        })
        
        mock_event2 = MagicMock()
        mock_event2.data = None
        
        mock_sse_client = MagicMock()
        mock_sse_client.events.return_value = [mock_event1, mock_event2]
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/event-stream"}
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('mcp_client.SSEClient', return_value=mock_sse_client):
                with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: request_id)):
                    result = await mcp_client._send_jsonrpc_request("tools/list")
                    
                    assert result == mock_result
    
    @pytest.mark.asyncio
    async def test_send_jsonrpc_request_error_response(self, mcp_client):
        """Test _send_jsonrpc_request with error response."""
        request_id = "test-request-id"
        error_data = {"code": -1, "message": "Test error"}
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error_data
        }
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: request_id)):
                with pytest.raises(Exception, match="MCP Error"):
                    await mcp_client._send_jsonrpc_request("tools/list")
    
    @pytest.mark.asyncio
    async def test_send_jsonrpc_request_unexpected_content_type(self, mcp_client):
        """Test _send_jsonrpc_request with unexpected content type."""
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: "test-id")):
                with pytest.raises(Exception, match="Unexpected Content-Type"):
                    await mcp_client._send_jsonrpc_request("tools/list")
    
    @pytest.mark.asyncio
    async def test_send_jsonrpc_request_no_response(self, mcp_client):
        """Test _send_jsonrpc_request when no response is received."""
        request_id = "test-request-id"
        
        mock_event = MagicMock()
        mock_event.data = json.dumps({
            "jsonrpc": "2.0",
            "id": "different-id",
            "result": {}
        })
        
        mock_sse_client = MagicMock()
        mock_sse_client.events.return_value = [mock_event]
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/event-stream"}
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('mcp_client.SSEClient', return_value=mock_sse_client):
                with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: request_id)):
                    with pytest.raises(Exception, match="No response received"):
                        await mcp_client._send_jsonrpc_request("tools/list")
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mcp_client):
        """Test successful initialization."""
        mock_result = {
            "tools": [
                {"name": "tool1", "description": "Tool 1"},
                {"name": "tool2", "description": "Tool 2"}
            ]
        }
        
        with patch.object(mcp_client, '_send_jsonrpc_request', return_value=mock_result):
            await mcp_client.initialize()
            
            assert mcp_client._initialized is True
            assert len(mcp_client.tools) == 2
            assert mcp_client.tools[0]["name"] == "tool1"
    
    @pytest.mark.asyncio
    async def test_initialize_with_list_result(self, mcp_client):
        """Test initialization when result is a list."""
        mock_result = [
            {"name": "tool1"},
            {"name": "tool2"}
        ]
        
        with patch.object(mcp_client, '_send_jsonrpc_request', return_value=mock_result):
            await mcp_client.initialize()
            
            assert mcp_client._initialized is True
            assert mcp_client.tools == mock_result
    
    @pytest.mark.asyncio
    async def test_initialize_with_empty_result(self, mcp_client):
        """Test initialization with empty result."""
        mock_result = {}
        
        with patch.object(mcp_client, '_send_jsonrpc_request', return_value=mock_result):
            await mcp_client.initialize()
            
            assert mcp_client._initialized is True
            assert mcp_client.tools == []
    
    @pytest.mark.asyncio
    async def test_initialize_error_handling(self, mcp_client):
        """Test initialization error handling."""
        with patch.object(mcp_client, '_send_jsonrpc_request', side_effect=Exception("Connection error")):
            with pytest.raises(Exception, match="Connection error"):
                await mcp_client.initialize()
            
            assert mcp_client._initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, mcp_client):
        """Test that initialize is idempotent."""
        mock_result = {"tools": []}
        
        with patch.object(mcp_client, '_send_jsonrpc_request', return_value=mock_result) as mock_request:
            await mcp_client.initialize()
            await mcp_client.initialize()  # Call again
            
            # Should only call once
            assert mock_request.call_count == 1
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_client):
        """Test successful tool call."""
        tool_name = "test_tool"
        arguments = {"param1": "value1"}
        mock_result = {"status": "success", "data": "result"}
        
        with patch.object(mcp_client, '_send_jsonrpc_request', return_value=mock_result):
            result = await mcp_client.call_tool(tool_name, arguments)
            
            assert result == mock_result
            mcp_client._send_jsonrpc_request.assert_called_once_with(
                "tools/call",
                params={
                    "name": tool_name,
                    "arguments": arguments
                }
            )
    
    @pytest.mark.asyncio
    async def test_call_tool_error_handling(self, mcp_client):
        """Test tool call error handling."""
        tool_name = "test_tool"
        arguments = {"param1": "value1"}
        
        with patch.object(mcp_client, '_send_jsonrpc_request', side_effect=Exception("Tool error")):
            with pytest.raises(Exception, match=f"Error calling tool {tool_name}"):
                await mcp_client.call_tool(tool_name, arguments)
    
    @pytest.mark.asyncio
    async def test_close(self, mcp_client):
        """Test closing the client."""
        await mcp_client.close()
        # Should not raise any errors
        # The actual httpx client close is tested implicitly


class TestGetMCPClient:
    """Test suite for get_mcp_client function."""
    
    @pytest.fixture(autouse=True)
    def reset_global_client(self):
        """Reset global client before each test."""
        import mcp_client
        mcp_client._client = None
        yield
        mcp_client._client = None
        if mcp_client._client is not None:
            # Clean up if needed
            pass
    
    @pytest.mark.asyncio
    async def test_get_mcp_client_creates_new_instance(self):
        """Test that get_mcp_client creates a new instance."""
        with patch.dict(os.environ, {'MCP_SERVER_URL': 'https://test-server.com/mcp'}):
            with patch('mcp_client.MCPClient') as mock_client_class:
                mock_instance = AsyncMock()
                mock_instance.initialize = AsyncMock()
                mock_client_class.return_value = mock_instance
                
                client1 = await get_mcp_client()
                client2 = await get_mcp_client()
                
                # Should return the same instance (singleton)
                assert client1 is client2
                # Should only create once
                assert mock_client_class.call_count == 1
                # Should initialize once
                assert mock_instance.initialize.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_mcp_client_uses_default_url(self):
        """Test that get_mcp_client uses default URL when env var not set."""
        default_url = 'https://vipfapwm3x.us-east-1.awsapprunner.com/mcp'
        
        with patch.dict(os.environ, {}, clear=True):
            with patch('mcp_client.MCPClient') as mock_client_class:
                mock_instance = AsyncMock()
                mock_instance.initialize = AsyncMock()
                mock_client_class.return_value = mock_instance
                
                await get_mcp_client()
                
                # MCPClient is called with positional argument
                mock_client_class.assert_called_once_with(default_url)
    
    @pytest.mark.asyncio
    async def test_get_mcp_client_uses_env_var(self):
        """Test that get_mcp_client uses MCP_SERVER_URL from environment."""
        custom_url = 'https://custom-server.com/mcp'
        
        with patch.dict(os.environ, {'MCP_SERVER_URL': custom_url}):
            with patch('mcp_client.MCPClient') as mock_client_class:
                mock_instance = AsyncMock()
                mock_instance.initialize = AsyncMock()
                mock_client_class.return_value = mock_instance
                
                await get_mcp_client()
                
                # MCPClient is called with positional argument
                mock_client_class.assert_called_once_with(custom_url)


class TestMCPClientIntegration:
    """Integration-style tests for MCPClient."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a full workflow: init -> initialize -> call_tool."""
        server_url = "https://test-server.com/mcp"
        client = MCPClient(server_url)
        
        # Mock the initialization
        init_result = {"tools": [{"name": "test_tool"}]}
        tool_result = {"output": "success"}
        
        with patch.object(client, '_send_jsonrpc_request') as mock_request:
            mock_request.side_effect = [init_result, tool_result]
            
            # Initialize
            await client.initialize()
            assert client._initialized is True
            assert len(client.tools) == 1
            
            # Call tool
            result = await client.call_tool("test_tool", {"param": "value"})
            assert result == tool_result
            
            # Verify calls
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_sse_stream_parsing(self):
        """Test SSE stream event parsing with multiple events."""
        server_url = "https://test-server.com/mcp"
        client = MCPClient(server_url)
        request_id = "test-id"
        
        # Create multiple events
        events_data = [
            json.dumps({"jsonrpc": "2.0", "id": "other-id", "result": {}}),
            json.dumps({"jsonrpc": "2.0", "id": request_id, "result": {"success": True}}),
        ]
        
        mock_events = []
        for data in events_data:
            event = MagicMock()
            event.data = data
            mock_events.append(event)
        
        mock_sse_client = MagicMock()
        mock_sse_client.events.return_value = mock_events
        
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/event-stream"}
        mock_response.raise_for_status = Mock()
        
        with patch('mcp_client.requests.post', return_value=mock_response):
            with patch('mcp_client.SSEClient', return_value=mock_sse_client):
                with patch('uuid.uuid4', return_value=Mock(__str__=lambda x: request_id)):
                    result = await client._send_jsonrpc_request("test/method")
                    
                    assert result == {"success": True}

