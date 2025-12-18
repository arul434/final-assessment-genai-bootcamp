#!/usr/bin/env python3
"""
Chat utility that integrates LLM client with MCP client for tool calling.
"""

import json
from typing import Optional, List, Dict, Any, AsyncIterator
from src.core.llm_client import (
    get_llm_client, 
    LLMClient,
    Message,
    ChatCompletionInput,
    ChatCompletionResponse,
    ToolDefinition,
    FunctionDefinition
)
from src.core.mcp_client import get_mcp_client, MCPClient


class ChatSession:
    """Manages a chat session with conversation history and tool integration."""
    
    def __init__(
        self,
        session_id: str,
        system_message: Optional[str] = None,
        llm_client: Optional[LLMClient] = None,
        mcp_client: Optional[MCPClient] = None
    ):
        """
        Initialize a chat session.
        
        Args:
            session_id: Unique session identifier
            system_message: System message for the LLM
            llm_client: Optional LLM client instance
            mcp_client: Optional MCP client instance
        """
        self.session_id = session_id
        self.conversation_history: List[Dict[str, Any]] = []
        self.system_message = system_message or self._default_system_message()
        self.llm_client = llm_client or get_llm_client()
        self.mcp_client = mcp_client
        self._mcp_tools_formatted: Optional[List[Dict[str, Any]]] = None
    
    def _default_system_message(self) -> str:
        """Default system message for customer support."""
        return """You are a helpful customer support agent for a company that sells computer products including monitors, printers, computers, and accessories.

Your responsibilities:
- Help customers find products they're looking for
- Provide detailed product information (SKU, price, inventory, descriptions)
- Assist with order placement and tracking
- Verify customer identity and provide account information when needed
- Provide excellent, friendly customer service

Available product categories: Computers, Monitors, Printers, Accessories

Guidelines:
- Always be polite and professional
- Use the available tools to look up accurate, real-time information
- Don't make up product details - always use the tools to get current data
- To verify a customer's identity, ask for their email and PIN, then use the verify_customer tool
- Once identity is verified using the tool, you can safely provide customer information including customer ID, order history, and account details
- When creating orders, confirm all details with the customer first
- Provide clear, concise responses
- If a customer asks about a product, search for it or list products in that category

Remember: You have access to real-time product inventory, customer data, and order management tools. Use them to help customers effectively!"""
    
    async def _get_mcp_client(self) -> MCPClient:
        """Get or initialize MCP client."""
        if self.mcp_client is None:
            self.mcp_client = await get_mcp_client()
        return self.mcp_client
    
    async def _get_tools_for_llm(self) -> Optional[List[ToolDefinition]]:
        """
        Convert MCP tools to OpenAI function calling format using Pydantic models.
        
        Returns:
            List of ToolDefinition models or None if no tools
        """
        if self._mcp_tools_formatted is not None:
            return self._mcp_tools_formatted
        
        mcp = await self._get_mcp_client()
        
        if not mcp.tools:
            return None
        
        # Convert MCP tools to Pydantic ToolDefinition models
        tools = []
        for tool in mcp.tools:
            # Extract tool information
            tool_name = tool.get("name", "")
            tool_desc = tool.get("description", "")
            tool_input = tool.get("inputSchema", {})
            
            # Ensure the schema has the correct structure for OpenAI
            # OpenAI requires the full JSON Schema with type: "object"
            if tool_input and "type" not in tool_input:
                # If no type specified, wrap it properly
                tool_input = {
                    "type": "object",
                    "properties": tool_input.get("properties", {}),
                    "required": tool_input.get("required", [])
                }
            elif not tool_input:
                # If no schema provided, use empty object schema
                tool_input = {
                    "type": "object",
                    "properties": {}
                }
            
            # Create Pydantic models
            function_def = FunctionDefinition(
                name=tool_name,
                description=tool_desc,
                parameters=tool_input
            )
            
            tool_def = ToolDefinition(
                type="function",
                function=function_def
            )
            tools.append(tool_def)
        
        self._mcp_tools_formatted = tools if tools else None
        return self._mcp_tools_formatted
    
    async def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool call via MCP client.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            JSON string of tool result
        """
        try:
            mcp = await self._get_mcp_client()
            result = await mcp.call_tool(tool_name, arguments)
            
            # Convert result to JSON string for LLM
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            elif isinstance(result, str):
                return result
            else:
                return str(result)
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
    
    async def chat(
        self,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_tool_iterations: int = 5
    ) -> str:
        """
        Process a user message and return assistant response.
        Handles tool calling automatically.
        
        Args:
            user_message: User's message
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
            max_tool_iterations: Maximum number of tool call iterations
            
        Returns:
            Assistant's final response
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Build messages for LLM using Pydantic models
        messages: List[Message] = []
        if self.system_message:
            messages.append(Message(role="system", content=self.system_message))
        
        # Convert conversation history to Message models
        for msg in self.conversation_history:
            messages.append(Message(
                role=msg["role"],
                content=msg.get("content"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id"),
                name=msg.get("name")
            ))
        
        # Get available tools
        tools = await self._get_tools_for_llm()
        
        # Conversation loop with tool calling
        iteration = 0
        while iteration < max_tool_iterations:
            iteration += 1
            
            # Create input using Pydantic model
            input_data = ChatCompletionInput(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None,
                stream=False
            )
            
            # Call LLM with tools
            response: ChatCompletionResponse = await self.llm_client.chat_completion(input_data)
            
            # Create assistant message
            assistant_message = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls
            )
            
            messages.append(assistant_message)
            
            # Check if LLM wants to call tools
            if not response.tool_calls:
                # No tool calls, we're done
                response_text = response.content or ""
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_text
                })
                return response_text
            
            # Execute tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    tool_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}
                
                # Execute tool
                tool_result = await self._execute_tool_call(tool_name, tool_args)
                
                # Add tool result to messages
                tool_results.append(Message(
                    role="tool",
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=tool_result
                ))
            
            # Add tool results to messages for next iteration
            messages.extend(tool_results)
        
        # If we hit max iterations, return the last response
        final_response = messages[-1].content if messages[-1].content else "I apologize, but I encountered an issue processing your request."
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response
        })
        return final_response
    
    async def chat_stream(
        self,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_tool_iterations: int = 5
    ) -> AsyncIterator[str]:
        """
        Process a user message and stream assistant response.
        Note: Tool calls are handled synchronously, then streaming continues.
        
        Args:
            user_message: User's message
            temperature: LLM temperature
            max_tokens: Maximum tokens to generate
            max_tool_iterations: Maximum number of tool call iterations
            
        Yields:
            Chunks of assistant response text
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Build messages for LLM using Pydantic models
        messages: List[Message] = []
        if self.system_message:
            messages.append(Message(role="system", content=self.system_message))
        
        # Convert conversation history to Message models
        for msg in self.conversation_history:
            messages.append(Message(
                role=msg["role"],
                content=msg.get("content"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id"),
                name=msg.get("name")
            ))
        
        # Get available tools
        tools = await self._get_tools_for_llm()
        
        # First, handle any tool calls (non-streaming)
        iteration = 0
        while iteration < max_tool_iterations:
            iteration += 1
            
            # Create input using Pydantic model
            input_data = ChatCompletionInput(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None,
                stream=False
            )
            
            # Check if we need tools (non-streaming call)
            response: ChatCompletionResponse = await self.llm_client.chat_completion(input_data)
            
            if not response.tool_calls:
                # No tool calls, break and stream response
                break
            
            # Create assistant message
            assistant_message = Message(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls
            )
            messages.append(assistant_message)
            
            # Execute tool calls
            tool_results = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["function"]["name"]
                try:
                    tool_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    tool_args = {}
                
                tool_result = await self._execute_tool_call(tool_name, tool_args)
                tool_results.append(Message(
                    role="tool",
                    tool_call_id=tool_call["id"],
                    name=tool_name,
                    content=tool_result
                ))
            
            messages.extend(tool_results)
        
        # Now stream the final response
        stream_input = ChatCompletionInput(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        full_response = ""
        async for chunk in self.llm_client.chat_completion_stream(stream_input):
            full_response += chunk
            yield chunk
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
    
    def reset(self):
        """Reset conversation history for this session."""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.conversation_history.copy()


# Global session storage
_sessions: Dict[str, ChatSession] = {}


async def get_chat_session(
    session_id: str,
    system_message: Optional[str] = None
) -> ChatSession:
    """
    Get or create a chat session.
    
    Args:
        session_id: Unique session identifier
        system_message: Optional system message override
        
    Returns:
        ChatSession instance
    """
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(
            session_id=session_id,
            system_message=system_message
        )
    return _sessions[session_id]


def reset_session(session_id: str):
    """Reset a chat session."""
    if session_id in _sessions:
        _sessions[session_id].reset()


def delete_session(session_id: str):
    """Delete a chat session."""
    if session_id in _sessions:
        del _sessions[session_id]


def get_all_sessions() -> Dict[str, "ChatSession"]:
    """Get all active sessions (for admin/debugging purposes)."""
    return _sessions.copy()
