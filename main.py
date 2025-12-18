#!/usr/bin/env python3
"""
Main entry point for the Customer Support Chatbot.
"""

import asyncio
from src.core.chat_util import get_chat_session


async def main():
    """Main function to demonstrate integrated chat with LLM and MCP."""
    print("Customer Support Chatbot - Integrated Chat Demo")
    print("=" * 60)
    
    try:
        # Create a chat session (integrates LLM + MCP)
        session = await get_chat_session(session_id="demo-session")
        
        print("\n📋 Available MCP Tools:")
        mcp = await session._get_mcp_client()
        for tool in mcp.tools:
            print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}")
        
        print("\n" + "=" * 60)
        print("💬 Chat Examples (with automatic tool calling):")
        print("=" * 60)
        
        # Example 1: Simple greeting
        print("\n1. User: Hello! Can you help me find a monitor?")
        response = await session.chat("Hello! Can you help me find a monitor?")
        print(f"   Assistant: {response}")
        
        # Example 2: Product search (will trigger MCP tool)
        print("\n2. User: Show me all available monitors")
        response = await session.chat("Show me all available monitors")
        print(f"   Assistant: {response[:200]}..." if len(response) > 200 else f"   Assistant: {response}")
        
        # Example 3: Conversation continues
        print("\n3. User: What about printers?")
        response = await session.chat("What about printers?")
        print(f"   Assistant: {response[:200]}..." if len(response) > 200 else f"   Assistant: {response}")
        
        print("\n" + "=" * 60)
        print("✅ Chat module is working correctly!")
        print(f"📊 Conversation history: {len(session.get_history())} messages")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please set the OPENAI_API_KEY environment variable.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
