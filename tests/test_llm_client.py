#!/usr/bin/env python3
"""
Unit tests for LLMClient.
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from openai import AsyncOpenAI
from src.core.llm_client import LLMClient, get_llm_client, ChatCompletionInput, Message


class TestLLMClient:
    """Test suite for LLMClient class."""
    
    @pytest.fixture
    def mock_api_key(self):
        """Fixture providing a mock API key."""
        return "test-api-key-12345"
    
    @pytest.fixture
    def mock_openai_client(self):
        """Fixture providing a mocked OpenAI client."""
        mock_client = AsyncMock(spec=AsyncOpenAI)
        mock_chat = AsyncMock()
        mock_completions = AsyncMock()
        mock_client.chat = mock_chat
        mock_chat.completions = mock_completions
        return mock_client, mock_completions
    
    def test_init_with_api_key(self, mock_api_key):
        """Test LLMClient initialization with explicit API key."""
        with patch('llm_client.AsyncOpenAI') as mock_openai:
            client = LLMClient(api_key=mock_api_key)
            
            assert client.api_key == mock_api_key
            assert client.model == "gpt-4o-mini"
            mock_openai.assert_called_once_with(
                api_key=mock_api_key,
                base_url=None
            )
    
    def test_init_with_env_var(self, mock_api_key):
        """Test LLMClient initialization with environment variable."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': mock_api_key}):
            with patch('llm_client.AsyncOpenAI') as mock_openai:
                client = LLMClient()
                
                assert client.api_key == mock_api_key
                mock_openai.assert_called_once()
    
    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                LLMClient()
    
    def test_init_with_custom_model(self, mock_api_key):
        """Test LLMClient initialization with custom model."""
        with patch('llm_client.AsyncOpenAI'):
            client = LLMClient(api_key=mock_api_key, model="gpt-4")
            assert client.model == "gpt-4"
    
    def test_init_with_base_url(self, mock_api_key):
        """Test LLMClient initialization with custom base URL."""
        base_url = "https://custom-api.example.com"
        with patch('llm_client.AsyncOpenAI') as mock_openai:
            client = LLMClient(api_key=mock_api_key, base_url=base_url)
            mock_openai.assert_called_once_with(
                api_key=mock_api_key,
                base_url=base_url
            )
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, mock_api_key, mock_openai_client):
        """Test successful chat completion."""
        mock_client, mock_completions = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        
        mock_completions.create = AsyncMock(return_value=mock_response)
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            input_data = ChatCompletionInput(
                messages=[Message(role="user", content="Hello")]
            )
            response = await client.chat_completion(input_data)
            
            assert response.content == "Test response"
            assert response.role == "assistant"
            mock_completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_custom_params(self, mock_api_key, mock_openai_client):
        """Test chat completion with custom parameters."""
        mock_client, mock_completions = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Custom response"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        
        mock_completions.create = AsyncMock(return_value=mock_response)
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            input_data = ChatCompletionInput(
                messages=[Message(role="user", content="Hello")],
                temperature=0.9,
                max_tokens=100,
                stream=False
            )
            response = await client.chat_completion(input_data)
            
            assert response.content == "Custom response"
            call_args = mock_completions.create.call_args
            assert call_args[1]['temperature'] == 0.9
            assert call_args[1]['max_tokens'] == 100
    
    @pytest.mark.asyncio
    async def test_chat_completion_error_handling(self, mock_api_key, mock_openai_client):
        """Test chat completion error handling."""
        mock_client, mock_completions = mock_openai_client
        
        mock_completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            input_data = ChatCompletionInput(
                messages=[Message(role="user", content="Hello")]
            )
            with pytest.raises(Exception, match="Error calling OpenAI API"):
                await client.chat_completion(input_data)
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream(self, mock_api_key, mock_openai_client):
        """Test streaming chat completion."""
        mock_client, mock_completions = mock_openai_client
        
        # Create mock stream chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " World"
        
        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
        
        mock_completions.create = AsyncMock(return_value=mock_stream())
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            input_data = ChatCompletionInput(
                messages=[Message(role="user", content="Hello")]
            )
            chunks = []
            async for chunk in client.chat_completion_stream(input_data):
                chunks.append(chunk)
            
            assert chunks == ["Hello", " World"]
    
    @pytest.mark.asyncio
    async def test_chat_completion_stream_error_handling(self, mock_api_key, mock_openai_client):
        """Test streaming chat completion error handling."""
        mock_client, mock_completions = mock_openai_client
        
        mock_completions.create = AsyncMock(side_effect=Exception("Stream Error"))
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            input_data = ChatCompletionInput(
                messages=[Message(role="user", content="Hello")]
            )
            with pytest.raises(Exception, match="Error streaming from OpenAI API"):
                async for _ in client.chat_completion_stream(input_data):
                    pass
    
    @pytest.mark.asyncio
    async def test_chat_completion_simple(self, mock_api_key, mock_openai_client):
        """Test simple chat completion."""
        mock_client, mock_completions = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Simple response"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        
        mock_completions.create = AsyncMock(return_value=mock_response)
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            response = await client.chat_completion_simple("Hello")
            
            assert response == "Simple response"
            call_args = mock_completions.create.call_args
            assert call_args[1]['messages'][-1]['role'] == 'user'
            assert call_args[1]['messages'][-1]['content'] == "Hello"
    
    @pytest.mark.asyncio
    async def test_chat_completion_simple_with_system_message(self, mock_api_key, mock_openai_client):
        """Test simple chat completion with system message."""
        mock_client, mock_completions = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Response with system"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        
        mock_completions.create = AsyncMock(return_value=mock_response)
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            response = await client.chat_completion_simple(
                "Hello",
                system_message="You are a helpful assistant"
            )
            
            assert response == "Response with system"
            call_args = mock_completions.create.call_args
            messages = call_args[1]['messages']
            assert messages[0]['role'] == 'system'
            assert messages[0]['content'] == "You are a helpful assistant"
            assert messages[1]['role'] == 'user'
            assert messages[1]['content'] == "Hello"
    
    @pytest.mark.asyncio
    async def test_chat_completion_simple_with_history(self, mock_api_key, mock_openai_client):
        """Test simple chat completion with conversation history."""
        mock_client, mock_completions = mock_openai_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Response with history"
        mock_response.choices[0].message.role = "assistant"
        mock_response.choices[0].message.tool_calls = None
        mock_response.choices[0].finish_reason = "stop"
        
        mock_completions.create = AsyncMock(return_value=mock_response)
        
        with patch('llm_client.AsyncOpenAI', return_value=mock_client):
            client = LLMClient(api_key=mock_api_key)
            
            history = [
                Message(role="user", content="First message"),
                Message(role="assistant", content="First response")
            ]
            
            response = await client.chat_completion_simple(
                "Second message",
                conversation_history=history
            )
            
            assert response == "Response with history"
            call_args = mock_completions.create.call_args
            messages = call_args[1]['messages']
            assert len(messages) == 3
            assert messages[0]['role'] == 'user'
            assert messages[0]['content'] == "First message"
            assert messages[1]['role'] == 'assistant'
            assert messages[1]['content'] == "First response"
            assert messages[2]['role'] == 'user'
            assert messages[2]['content'] == "Second message"


class TestGetLLMClient:
    """Test suite for get_llm_client function."""
    
    @pytest.fixture(autouse=True)
    def reset_global_client(self):
        """Reset global client before each test."""
        import llm_client
        llm_client._client = None
        yield
        llm_client._client = None
    
    def test_get_llm_client_creates_new_instance(self):
        """Test that get_llm_client creates a new instance."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('llm_client.LLMClient') as mock_client_class:
                mock_instance = MagicMock()
                mock_client_class.return_value = mock_instance
                
                client1 = get_llm_client()
                client2 = get_llm_client()
                
                # Should return the same instance (singleton)
                assert client1 is client2
                # But should only create once
                assert mock_client_class.call_count == 1
    
    def test_get_llm_client_with_custom_model(self):
        """Test get_llm_client with custom model."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('llm_client.LLMClient') as mock_client_class:
                mock_instance = MagicMock()
                mock_client_class.return_value = mock_instance
                
                client = get_llm_client(model="gpt-4")
                
                mock_client_class.assert_called_once_with(
                    api_key=None,
                    model="gpt-4"
                )
    
    def test_get_llm_client_with_api_key(self):
        """Test get_llm_client with explicit API key."""
        with patch('llm_client.LLMClient') as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            
            client = get_llm_client(api_key="custom-key")
            
            mock_client_class.assert_called_once_with(
                api_key="custom-key",
                model="gpt-4o-mini"
            )

