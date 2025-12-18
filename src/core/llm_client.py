#!/usr/bin/env python3
"""
OpenAI LLM Client for handling all LLM interactions.
"""

import os
from typing import Optional, List, Dict, Any, AsyncIterator, Literal
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Pydantic Models for Input/Output

class Message(BaseModel):
    """Message model for chat conversations."""
    role: Literal["system", "user", "assistant", "tool"] = Field(..., description="Message role")
    content: Optional[str] = Field(None, description="Message content")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls in this message")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")
    name: Optional[str] = Field(None, description="Tool name for tool responses")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for OpenAI API."""
        result = {"role": self.role}
        if self.content is not None:
            result["content"] = self.content
        if self.tool_calls is not None:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        if self.name is not None:
            result["name"] = self.name
        return result


class FunctionDefinition(BaseModel):
    """Function/tool definition for OpenAI function calling."""
    name: str = Field(..., description="Function name")
    description: str = Field(..., description="Function description")
    parameters: Dict[str, Any] = Field(..., description="Function parameters schema")


class ToolDefinition(BaseModel):
    """Tool definition for OpenAI function calling."""
    type: Literal["function"] = Field("function", description="Tool type")
    function: FunctionDefinition = Field(..., description="Function definition")


class ChatCompletionInput(BaseModel):
    """Input model for chat completion requests."""
    messages: List[Message] = Field(..., description="List of messages in the conversation")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    tools: Optional[List[ToolDefinition]] = Field(None, description="Available tools/functions")
    tool_choice: Optional[Literal["none", "auto", "required"]] = Field(None, description="Tool choice strategy")
    stream: bool = Field(False, description="Whether to stream the response")
    
    def to_openai_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for OpenAI API."""
        result = {
            "messages": [msg.to_dict() for msg in self.messages],
            "temperature": self.temperature,
            "stream": self.stream
        }
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.tools is not None:
            result["tools"] = [tool.model_dump() for tool in self.tools]
        if self.tool_choice is not None:
            result["tool_choice"] = self.tool_choice
        return result


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""
    content: Optional[str] = Field(None, description="Assistant response content")
    role: str = Field("assistant", description="Message role")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls requested by the model")
    finish_reason: Optional[str] = Field(None, description="Reason for completion finish")
    
    @classmethod
    def from_openai_response(cls, response: Any) -> "ChatCompletionResponse":
        """Create from OpenAI API response."""
        message = response.choices[0].message
        return cls(
            content=message.content,
            role=message.role,
            tool_calls=[
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in (message.tool_calls or [])
            ] if message.tool_calls else None,
            finish_reason=response.choices[0].finish_reason
        )


class LLMClient:
    """Client for interacting with OpenAI API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None
    ):
        """
        Initialize OpenAI LLM client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (defaults to gpt-4o-mini for cost efficiency)
            base_url: Optional base URL for custom endpoints
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable."
            )
        
        self.model = model
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )
    
    async def chat_completion(
        self,
        input_data: ChatCompletionInput,
        **kwargs
    ) -> ChatCompletionResponse:
        """
        Generate a chat completion.
        
        Args:
            input_data: ChatCompletionInput model with all parameters
            **kwargs: Additional parameters for OpenAI API (will override input_data)
            
        Returns:
            ChatCompletionResponse model
        """
        try:
            # Convert input to OpenAI format
            openai_params = input_data.to_openai_dict()
            openai_params.update(kwargs)
            
            # Add model
            openai_params["model"] = self.model
            
            response = await self.client.chat.completions.create(**openai_params)
            
            # Convert to our response model
            return ChatCompletionResponse.from_openai_response(response)
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    async def chat_completion_raw(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Generate a chat completion using raw dictionaries (for backward compatibility).
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            tools: Optional tools in dict format
            tool_choice: Tool choice strategy
            **kwargs: Additional parameters for OpenAI API
            
        Returns:
            Raw OpenAI response or async iterator if streaming
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream,
                **kwargs
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if tools is not None:
                params["tools"] = tools
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
            
            response = await self.client.chat.completions.create(**params)
            return response
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    async def chat_completion_stream(
        self,
        input_data: ChatCompletionInput,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat completion.
        
        Args:
            input_data: ChatCompletionInput model with all parameters
            **kwargs: Additional parameters for OpenAI API
            
        Yields:
            Chunks of text as they are generated
        """
        try:
            # Create input with streaming enabled
            stream_input = input_data.model_copy()
            stream_input.stream = True
            
            # Convert to OpenAI format
            openai_params = stream_input.to_openai_dict()
            openai_params.update(kwargs)
            openai_params["model"] = self.model
            
            stream = await self.client.chat.completions.create(**openai_params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Error streaming from OpenAI API: {str(e)}")
    
    async def chat_completion_stream_raw(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat completion using raw dictionaries (for backward compatibility).
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            tools: Optional tools in dict format
            tool_choice: Tool choice strategy
            **kwargs: Additional parameters for OpenAI API
            
        Yields:
            Chunks of text as they are generated
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                **kwargs
            }
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if tools is not None:
                params["tools"] = tools
            if tool_choice is not None:
                params["tool_choice"] = tool_choice
            
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Error streaming from OpenAI API: {str(e)}")
    
    async def chat_completion_simple(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Message]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Simple chat completion that returns just the text response.
        
        Args:
            user_message: The user's message
            system_message: Optional system message
            conversation_history: Optional previous conversation messages (as Message models)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            The assistant's response text
        """
        messages = []
        
        if system_message:
            messages.append(Message(role="system", content=system_message))
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append(Message(role="user", content=user_message))
        
        input_data = ChatCompletionInput(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )
        
        response = await self.chat_completion(input_data)
        
        return response.content or ""


# Global client instance
_client: Optional[LLMClient] = None


def get_llm_client(
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None
) -> LLMClient:
    """
    Get or create LLM client instance.
    
    Args:
        model: Model to use (defaults to gpt-4o-mini)
        api_key: Optional API key override
        
    Returns:
        Initialized LLMClient instance
    """
    global _client
    
    if _client is None:
        _client = LLMClient(api_key=api_key, model=model)
    
    return _client

