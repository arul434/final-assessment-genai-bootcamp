#!/usr/bin/env python3
"""
Test script to verify MCP server connection and list available tools.
"""

import asyncio
import os
import sys

# Ensure project root is on sys.path when running this file directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.mcp_client import get_mcp_client


async def main():
    """Test MCP client connection."""
    print("=" * 60)
    print("Testing MCP Server Connection")
    print("=" * 60)
    
    try:
        # Get MCP client
        client = await get_mcp_client()
        
        print(f"\n✓ Successfully connected to MCP server")
        print(f"✓ Found {len(client.tools)} tools\n")
        
        # Display tools
        print("Available MCP Tools:")
        print("-" * 60)
        for i, tool in enumerate(client.tools, 1):
            print(f"\n{i}. {tool['name']}")
            print(f"   Description: {tool.get('description', 'N/A')}")
            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print(f"   Parameters: {', '.join(schema['properties'].keys())}")
        
        print("\n" + "=" * 60)
        print("MCP Client Test Completed Successfully!")
        print("=" * 60)
        
        await client.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
