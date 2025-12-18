#!/usr/bin/env python3
"""
Simple script to run the FastAPI server.
"""

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting server on http://{host}:{port}")
    print(f"API docs available at http://{host}:{port}/docs")
    print(f"Health check at http://{host}:{port}/health")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug"
    )

