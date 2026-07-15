"""
chatui/server/
FastAPI server builder and WebSocket handler.
"""
from .builder import build_fastapi_app
from .ws import handle_websocket

__all__ = ["build_fastapi_app", "handle_websocket"]
