"""
WebSocket Package

This package provides real-time WebSocket communication for the
Traffic Intelligence System using Socket.IO.

Components:
- events: Event type definitions and data models
- emitter: Server→Client event emission
- handlers: Client→Server event handling

Usage:
    from app.websocket import WebSocketEmitter, WebSocketHandlers
    
    # Initialize with Socket.IO server
    emitter = WebSocketEmitter(sio)
    handlers = WebSocketHandlers(sio, emitter)
"""

from .events import ServerEvent, ClientEvent
from .emitter import WebSocketEmitter, get_emitter, set_emitter
from .handlers import WebSocketHandlers, get_handlers, set_handlers

__all__ = [
    "ServerEvent",
    "ClientEvent",
    "WebSocketEmitter",
    "WebSocketHandlers",
    "get_emitter",
    "set_emitter",
    "get_handlers",
    "set_handlers",
]
