#!/usr/bin/env python3
"""
Unit tests for chat_util.py
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from src.core.chat_util import (
    ChatSession,
    get_chat_session,
    reset_session,
    delete_session,
    get_all_sessions
)
from src.core.llm_client import Message, ChatCompletionResponse, ToolDefinition, FunctionDefinition
from src.core.mcp_client import MCPClient


class TestChatSession:
    """Test suite for ChatSession class."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Fixture providing a mocked LLM client."""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Fixture providing a mocked MCP client."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.tools = []
        return mock_client
    
    def test_init_with_defaults(self):
        """Test ChatSession initialization with defaults."""
        session = ChatSession(session_id="test-123")
        
        assert session.session_id == "test-123"
        assert session.conversation_history == []
        assert session.system_message is not None
        assert "customer support" in session.system_message.lower()
        assert session.llm_client is not None
        assert session.mcp_client is None
        assert session._mcp_tools_formatted is None
    
    def test_init_with_custom_system_message(self):
        """Test ChatSession initialization with custom system message."""
        custom_message = "You are a test assistant."
        session = ChatSession(
            session_id="test-123",
            system_message=custom_message
        )
        
        assert session.system_message == custom_message
    
    def test_init_with_custom_clients(self, mock_llm_client, mock_mcp_client):
        """Test ChatSession initialization with custom clients."""
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client,
            mcp_client=mock_mcp_client
        )
        
        assert session.llm_client is mock_llm_client
        assert session.mcp_client is mock_mcp_client
    
    def test_default_system_message(self):
        """Test that default system message contains expected content."""
        session = ChatSession(session_id="test-123")
        message = session._default_system_message()
        
        assert isinstance(message, str)
        assert len(message) > 0
        assert "customer support" in message.lower()
        assert "tools" in message.lower()
    
    @pytest.mark.asyncio
    async def test_get_mcp_client_with_existing(self, mock_mcp_client):
        """Test _get_mcp_client with existing client."""
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._get_mcp_client()
        assert result is mock_mcp_client
    
    @pytest.mark.asyncio
    async def test_get_mcp_client_creates_new(self):
        """Test _get_mcp_client creates new client when None."""
        with patch('chat_util.get_mcp_client') as mock_get_mcp:
            mock_client = AsyncMock(spec=MCPClient)
            mock_get_mcp.return_value = mock_client
            
            session = ChatSession(session_id="test-123")
            result = await session._get_mcp_client()
            
            assert result is mock_client
            assert session.mcp_client is mock_client
            mock_get_mcp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_tools_for_llm_no_tools(self, mock_mcp_client):
        """Test _get_tools_for_llm when no tools available."""
        mock_mcp_client.tools = []
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._get_tools_for_llm()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_tools_for_llm_with_tools(self, mock_mcp_client):
        """Test _get_tools_for_llm converts MCP tools to ToolDefinition."""
        mock_mcp_client.tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {
                    "properties": {
                        "param1": {"type": "string"}
                    }
                }
            }
        ]
        
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._get_tools_for_llm()
        
        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], ToolDefinition)
        assert result[0].function.name == "test_tool"
        assert result[0].function.description == "A test tool"
    
    @pytest.mark.asyncio
    async def test_get_tools_for_llm_caches_result(self, mock_mcp_client):
        """Test that _get_tools_for_llm caches the result."""
        mock_mcp_client.tools = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"properties": {}}
            }
        ]
        
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result1 = await session._get_tools_for_llm()
        result2 = await session._get_tools_for_llm()
        
        assert result1 is result2  # Should be the same cached object
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_success_dict(self, mock_mcp_client):
        """Test _execute_tool_call with dict result."""
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "success"})
        
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._execute_tool_call("test_tool", {"param": "value"})
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["result"] == "success"
        mock_mcp_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_success_string(self, mock_mcp_client):
        """Test _execute_tool_call with string result."""
        mock_mcp_client.call_tool = AsyncMock(return_value="simple string result")
        
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._execute_tool_call("test_tool", {})
        
        assert result == "simple string result"
    
    @pytest.mark.asyncio
    async def test_execute_tool_call_error_handling(self, mock_mcp_client):
        """Test _execute_tool_call error handling."""
        mock_mcp_client.call_tool = AsyncMock(side_effect=Exception("Tool error"))
        
        session = ChatSession(
            session_id="test-123",
            mcp_client=mock_mcp_client
        )
        
        result = await session._execute_tool_call("test_tool", {})
        
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Tool execution failed" in parsed["error"]
    
    @pytest.mark.asyncio
    async def test_chat_simple_no_tools(self, mock_llm_client):
        """Test chat method without tool calls."""
        mock_response = ChatCompletionResponse(
            content="Hello! How can I help you?",
            role="assistant",
            tool_calls=None,
            finish_reason="stop"
        )
        mock_llm_client.chat_completion = AsyncMock(return_value=mock_response)
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client
        )
        
        response = await session.chat("Hello")
        
        assert response == "Hello! How can I help you?"
        assert len(session.conversation_history) == 2  # user + assistant
        assert session.conversation_history[0]["role"] == "user"
        assert session.conversation_history[0]["content"] == "Hello"
        assert session.conversation_history[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_chat_with_tool_calls(self, mock_llm_client, mock_mcp_client):
        """Test chat method with tool calls."""
        # First response: wants to call a tool
        tool_response = ChatCompletionResponse(
            content=None,
            role="assistant",
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "arguments": json.dumps({"param": "value"})
                    }
                }
            ],
            finish_reason="tool_calls"
        )
        
        # Second response: final answer
        final_response = ChatCompletionResponse(
            content="Here's the result: success",
            role="assistant",
            tool_calls=None,
            finish_reason="stop"
        )
        
        mock_llm_client.chat_completion = AsyncMock(side_effect=[tool_response, final_response])
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "success"})
        mock_mcp_client.tools = []
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client,
            mcp_client=mock_mcp_client
        )
        
        response = await session.chat("Use test_tool")
        
        assert response == "Here's the result: success"
        assert mock_llm_client.chat_completion.call_count == 2
        mock_mcp_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
    
    @pytest.mark.asyncio
    async def test_chat_max_iterations(self, mock_llm_client, mock_mcp_client):
        """Test chat method respects max_tool_iterations."""
        # Always return tool calls
        tool_response = ChatCompletionResponse(
            content="Processing...",
            role="assistant",
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "arguments": "{}"
                    }
                }
            ],
            finish_reason="tool_calls"
        )
        
        mock_llm_client.chat_completion = AsyncMock(return_value=tool_response)
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "ok"})
        mock_mcp_client.tools = []
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client,
            mcp_client=mock_mcp_client
        )
        
        response = await session.chat("Test", max_tool_iterations=2)
        
        # Should hit max iterations
        assert mock_llm_client.chat_completion.call_count == 2
        # Response should be the last assistant message content or fallback message
        assert response is not None
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_chat_stream_no_tools(self, mock_llm_client):
        """Test chat_stream method without tool calls."""
        mock_response = ChatCompletionResponse(
            content="Streaming response",
            role="assistant",
            tool_calls=None,
            finish_reason="stop"
        )
        mock_llm_client.chat_completion = AsyncMock(return_value=mock_response)
        
        async def mock_stream(input_data):
            chunks = ["Hello", " ", "World"]
            for chunk in chunks:
                yield chunk
        
        # Return the async generator function directly
        mock_llm_client.chat_completion_stream = mock_stream
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client
        )
        
        chunks = []
        async for chunk in session.chat_stream("Hello"):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " ", "World"]
        assert len(session.conversation_history) == 2
        assert session.conversation_history[-1]["content"] == "Hello World"
    
    @pytest.mark.asyncio
    async def test_chat_stream_with_tools(self, mock_llm_client, mock_mcp_client):
        """Test chat_stream method with tool calls."""
        # First response: wants to call a tool
        tool_response = ChatCompletionResponse(
            content=None,
            role="assistant",
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "arguments": "{}"
                    }
                }
            ],
            finish_reason="tool_calls"
        )
        
        # Second response: no more tool calls, ready to stream
        no_tool_response = ChatCompletionResponse(
            content=None,
            role="assistant",
            tool_calls=None,
            finish_reason="stop"
        )
        
        # First call returns tool response, second call (after tool execution) returns no tools
        mock_llm_client.chat_completion = AsyncMock(side_effect=[tool_response, no_tool_response])
        
        async def mock_stream(input_data):
            chunks = ["Result", " ", "here"]
            for chunk in chunks:
                yield chunk
        
        # Return the async generator function directly
        mock_llm_client.chat_completion_stream = mock_stream
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "ok"})
        mock_mcp_client.tools = []
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client,
            mcp_client=mock_mcp_client
        )
        
        chunks = []
        async for chunk in session.chat_stream("Use tool"):
            chunks.append(chunk)
        
        assert chunks == ["Result", " ", "here"]
        # Should call chat_completion twice: once for tool call, once to check if more tools needed
        assert mock_llm_client.chat_completion.call_count == 2
        assert mock_mcp_client.call_tool.called
    
    def test_reset(self):
        """Test reset method clears conversation history."""
        session = ChatSession(session_id="test-123")
        session.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        
        session.reset()
        
        assert session.conversation_history == []
    
    def test_get_history(self):
        """Test get_history returns a copy of conversation history."""
        session = ChatSession(session_id="test-123")
        session.conversation_history = [
            {"role": "user", "content": "Hello"}
        ]
        
        history = session.get_history()
        
        assert history == session.conversation_history
        assert history is not session.conversation_history  # Should be a copy
        # Modifying the copy shouldn't affect original
        history.append({"role": "assistant", "content": "Hi"})
        assert len(session.conversation_history) == 1


class TestSessionManagement:
    """Test suite for global session management functions."""
    
    @pytest.fixture(autouse=True)
    def reset_sessions(self):
        """Reset sessions before each test."""
        import chat_util
        chat_util._sessions = {}
        yield
        chat_util._sessions = {}
    
    @pytest.mark.asyncio
    async def test_get_chat_session_creates_new(self):
        """Test get_chat_session creates a new session."""
        with patch('chat_util.ChatSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            session = await get_chat_session("new-session")
            
            assert session is mock_session
            mock_session_class.assert_called_once_with(
                session_id="new-session",
                system_message=None
            )
    
    @pytest.mark.asyncio
    async def test_get_chat_session_returns_existing(self):
        """Test get_chat_session returns existing session."""
        with patch('chat_util.ChatSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            session1 = await get_chat_session("existing-session")
            session2 = await get_chat_session("existing-session")
            
            assert session1 is session2
            assert mock_session_class.call_count == 1  # Only created once
    
    @pytest.mark.asyncio
    async def test_get_chat_session_with_system_message(self):
        """Test get_chat_session with custom system message."""
        with patch('chat_util.ChatSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            await get_chat_session("test-session", system_message="Custom message")
            
            mock_session_class.assert_called_once_with(
                session_id="test-session",
                system_message="Custom message"
            )
    
    def test_reset_session_exists(self):
        """Test reset_session with existing session."""
        import chat_util
        
        # Create a session
        session = ChatSession(session_id="test-123")
        session.conversation_history = [{"role": "user", "content": "Hello"}]
        chat_util._sessions["test-123"] = session
        
        reset_session("test-123")
        
        assert session.conversation_history == []
    
    def test_reset_session_not_exists(self):
        """Test reset_session with non-existent session."""
        # Should not raise an error
        reset_session("non-existent")
    
    def test_delete_session_exists(self):
        """Test delete_session with existing session."""
        import chat_util
        
        session = ChatSession(session_id="test-123")
        chat_util._sessions["test-123"] = session
        
        delete_session("test-123")
        
        assert "test-123" not in chat_util._sessions
    
    def test_delete_session_not_exists(self):
        """Test delete_session with non-existent session."""
        # Should not raise an error
        delete_session("non-existent")
    
    def test_get_all_sessions(self):
        """Test get_all_sessions returns copy of all sessions."""
        import chat_util
        
        session1 = ChatSession(session_id="session-1")
        session2 = ChatSession(session_id="session-2")
        chat_util._sessions = {
            "session-1": session1,
            "session-2": session2
        }
        
        all_sessions = get_all_sessions()
        
        assert len(all_sessions) == 2
        assert all_sessions["session-1"] is session1
        assert all_sessions["session-2"] is session2
        assert all_sessions is not chat_util._sessions  # Should be a copy


class TestChatSessionIntegration:
    """Integration tests for ChatSession."""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Fixture providing a mocked LLM client."""
        mock_client = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Fixture providing a mocked MCP client."""
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.tools = []
        return mock_client
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, mock_llm_client):
        """Test a full conversation flow with multiple messages."""
        responses = [
            ChatCompletionResponse(
                content="Hello! How can I help?",
                role="assistant",
                tool_calls=None,
                finish_reason="stop"
            ),
            ChatCompletionResponse(
                content="Goodbye!",
                role="assistant",
                tool_calls=None,
                finish_reason="stop"
            )
        ]
        
        mock_llm_client.chat_completion = AsyncMock(side_effect=responses)
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client
        )
        
        response1 = await session.chat("Hello")
        response2 = await session.chat("Goodbye")
        
        assert response1 == "Hello! How can I help?"
        assert response2 == "Goodbye!"
        assert len(session.conversation_history) == 4  # 2 user + 2 assistant
        assert session.conversation_history[0]["content"] == "Hello"
        assert session.conversation_history[1]["content"] == "Hello! How can I help?"
        assert session.conversation_history[2]["content"] == "Goodbye"
        assert session.conversation_history[3]["content"] == "Goodbye!"
    
    @pytest.mark.asyncio
    async def test_tool_call_with_invalid_json(self, mock_llm_client, mock_mcp_client):
        """Test tool call handling with invalid JSON arguments."""
        tool_response = ChatCompletionResponse(
            content=None,
            role="assistant",
            tool_calls=[
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "arguments": "invalid json{"
                    }
                }
            ],
            finish_reason="tool_calls"
        )
        
        final_response = ChatCompletionResponse(
            content="Done",
            role="assistant",
            tool_calls=None,
            finish_reason="stop"
        )
        
        mock_llm_client.chat_completion = AsyncMock(side_effect=[tool_response, final_response])
        mock_mcp_client.call_tool = AsyncMock(return_value={"result": "ok"})
        mock_mcp_client.tools = []
        
        session = ChatSession(
            session_id="test-123",
            llm_client=mock_llm_client,
            mcp_client=mock_mcp_client
        )
        
        response = await session.chat("Test")
        
        # Should handle invalid JSON gracefully (empty dict)
        mock_mcp_client.call_tool.assert_called_once_with("test_tool", {})
        assert response == "Done"
