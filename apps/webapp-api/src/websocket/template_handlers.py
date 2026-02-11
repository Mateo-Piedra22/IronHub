"""
Template WebSocket Handlers

This module provides WebSocket handlers for real-time template updates,
preview progress, and analytics notifications.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from ...core.deps import get_db, require_gestion_access
from ...core.auth import get_current_user_ws
from ...models.orm_models import Usuario
from ...services.template_service import TemplateService
from ...models.template_responses import (
    PreviewProgressMessage,
    TemplateUpdateMessage,
    AnalyticsUpdateMessage
)

logger = logging.getLogger(__name__)


class TemplateWebSocketManager:
    """WebSocket connection manager for template operations"""
    
    def __init__(self):
        # Store active connections by user and gym
        self.active_connections: Dict[int, List[WebSocket]] = {}  # user_id -> [WebSocket]
        self.gym_connections: Dict[int, List[WebSocket]] = {}     # gym_id -> [WebSocket]
        self.template_connections: Dict[int, List[WebSocket]] = {}  # template_id -> [WebSocket]
        
        # Background tasks
        self.background_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, gym_id: Optional[int] = None):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        
        # Store by user
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Store by gym if provided
        if gym_id:
            if gym_id not in self.gym_connections:
                self.gym_connections[gym_id] = []
            self.gym_connections[gym_id].append(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}, gym {gym_id}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connected",
            "user_id": user_id,
            "gym_id": gym_id,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int, gym_id: Optional[int] = None):
        """Remove WebSocket connection"""
        # Remove from user connections
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from gym connections
        if gym_id and gym_id in self.gym_connections:
            self.gym_connections[gym_id].remove(websocket)
            if not self.gym_connections[gym_id]:
                del self.gym_connections[gym_id]
        
        # Remove from template connections
        for template_id, connections in self.template_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del self.template_connections[template_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def send_to_user(self, user_id: int, message: Dict[str, Any]):
        """Send message to all connections for a user"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)
    
    async def send_to_gym(self, gym_id: int, message: Dict[str, Any]):
        """Send message to all connections for a gym"""
        if gym_id in self.gym_connections:
            disconnected = []
            for connection in self.gym_connections[gym_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.gym_connections[gym_id].remove(conn)
    
    async def send_to_template_subscribers(self, template_id: int, message: Dict[str, Any]):
        """Send message to all connections subscribed to a template"""
        if template_id in self.template_connections:
            disconnected = []
            for connection in self.template_connections[template_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.template_connections[template_id].remove(conn)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all active connections"""
        for user_id, connections in self.active_connections.items():
            disconnected = []
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                connections.remove(conn)
    
    def subscribe_to_template(self, websocket: WebSocket, template_id: int):
        """Subscribe connection to template updates"""
        if template_id not in self.template_connections:
            self.template_connections[template_id] = []
        self.template_connections[template_id].append(websocket)
    
    def unsubscribe_from_template(self, websocket: WebSocket, template_id: int):
        """Unsubscribe connection from template updates"""
        if template_id in self.template_connections:
            if websocket in self.template_connections[template_id]:
                self.template_connections[template_id].remove(websocket)
                if not self.template_connections[template_id]:
                    del self.template_connections[template_id]


# Global WebSocket manager instance
manager = TemplateWebSocketManager()


async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    gym_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Main WebSocket endpoint for template operations"""
    try:
        # Authenticate user
        current_user = await get_current_user_ws(token, db)
        if not current_user:
            await websocket.close(code=4001, reason="Authentication failed")
            return
        
        # Connect
        await manager.connect(websocket, current_user.id, gym_id)
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                await handle_websocket_message(
                    message=message,
                    websocket=websocket,
                    user_id=current_user.id,
                    gym_id=gym_id,
                    db=db
                )
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Internal server error"
                }, websocket)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, current_user.id, gym_id)


async def handle_websocket_message(
    message: Dict[str, Any],
    websocket: WebSocket,
    user_id: int,
    gym_id: Optional[int],
    db: Session
):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "subscribe_template":
        template_id = message.get("template_id")
        if template_id:
            manager.subscribe_to_template(websocket, template_id)
            await manager.send_personal_message({
                "type": "subscribed",
                "template_id": template_id
            }, websocket)
    
    elif message_type == "unsubscribe_template":
        template_id = message.get("template_id")
        if template_id:
            manager.unsubscribe_from_template(websocket, template_id)
            await manager.send_personal_message({
                "type": "unsubscribed",
                "template_id": template_id
            }, websocket)
    
    elif message_type == "ping":
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    else:
        await manager.send_personal_message({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }, websocket)


# === Template Update Notifications ===

async def notify_template_created(template_id: int, template_data: Dict[str, Any], user_id: int):
    """Notify clients when a template is created"""
    message = TemplateUpdateMessage(
        template_id=template_id,
        action="created",
        template_data=template_data
    ).dict()
    
    # Send to creator
    await manager.send_to_user(user_id, message)
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)


async def notify_template_updated(template_id: int, template_data: Dict[str, Any], user_id: int):
    """Notify clients when a template is updated"""
    message = TemplateUpdateMessage(
        template_id=template_id,
        action="updated",
        template_data=template_data
    ).dict()
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)
    
    # Send to updater
    await manager.send_to_user(user_id, message)


async def notify_template_deleted(template_id: int, user_id: int):
    """Notify clients when a template is deleted"""
    message = TemplateUpdateMessage(
        template_id=template_id,
        action="deleted"
    ).dict()
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)
    
    # Send to deleter
    await manager.send_to_user(user_id, message)


async def notify_template_assigned(template_id: int, gym_id: int, assignment_data: Dict[str, Any]):
    """Notify clients when a template is assigned to a gym"""
    message = {
        "type": "template_assigned",
        "template_id": template_id,
        "gym_id": gym_id,
        "assignment": assignment_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to gym members
    await manager.send_to_gym(gym_id, message)
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)


# === Preview Progress Notifications ===

async def notify_preview_progress(
    template_id: int,
    progress: float,
    status: str,
    message: Optional[str] = None,
    preview_url: Optional[str] = None
):
    """Notify clients about preview generation progress"""
    progress_message = PreviewProgressMessage(
        template_id=template_id,
        progress=progress,
        status=status,
        message=message,
        preview_url=preview_url
    ).dict()
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, progress_message)


async def notify_preview_completed(template_id: int, preview_url: str, generation_time: float):
    """Notify clients when preview generation is completed"""
    message = {
        "type": "preview_completed",
        "template_id": template_id,
        "preview_url": preview_url,
        "generation_time": generation_time,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)


async def notify_preview_failed(template_id: int, error_message: str):
    """Notify clients when preview generation fails"""
    message = {
        "type": "preview_failed",
        "template_id": template_id,
        "error": error_message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Send to template subscribers
    await manager.send_to_template_subscribers(template_id, message)


# === Analytics Notifications ===

async def notify_analytics_update(
    template_id: Optional[int] = None,
    gym_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None
):
    """Notify clients about analytics updates"""
    message = AnalyticsUpdateMessage(
        template_id=template_id,
        gym_id=gym_id,
        data=data or {}
    ).dict()
    
    # Send to specific template subscribers
    if template_id:
        await manager.send_to_template_subscribers(template_id, message)
    
    # Send to specific gym members
    if gym_id:
        await manager.send_to_gym(gym_id, message)
    
    # Broadcast to all if no specific targets
    if not template_id and not gym_id:
        await manager.broadcast(message)


# === Background Task Management ===

async def start_background_preview_generation(
    template_id: int,
    user_id: int,
    format: str,
    quality: str,
    sample_data: Optional[Dict[str, Any]] = None
):
    """Start background preview generation with progress notifications"""
    task_id = f"preview_{template_id}_{datetime.utcnow().timestamp()}"
    
    # Create background task
    task = asyncio.create_task(
        background_preview_generation(
            template_id=template_id,
            user_id=user_id,
            format=format,
            quality=quality,
            sample_data=sample_data,
            task_id=task_id
        )
    )
    
    manager.background_tasks[task_id] = task
    
    try:
        await task
    finally:
        # Clean up task
        if task_id in manager.background_tasks:
            del manager.background_tasks[task_id]


async def background_preview_generation(
    template_id: int,
    user_id: int,
    format: str,
    quality: str,
    sample_data: Optional[Dict[str, Any]],
    task_id: str
):
    """Background task for preview generation with progress updates"""
    try:
        # Notify start
        await notify_preview_progress(template_id, 0, "started", "Starting preview generation...")
        
        # Simulate progress (in real implementation, this would be actual progress)
        for progress in [10, 25, 50, 75, 90]:
            await asyncio.sleep(0.5)  # Simulate work
            await notify_preview_progress(
                template_id,
                progress,
                "generating",
                f"Generating preview... {progress}%"
            )
        
        # Generate actual preview (this would use the template service)
        # For now, simulate completion
        await asyncio.sleep(1)
        
        # Notify completion
        preview_url = f"/previews/template_{template_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        await notify_preview_completed(template_id, preview_url, 3.2)
        
        logger.info(f"Background preview generation completed for template {template_id}")
        
    except Exception as e:
        logger.error(f"Background preview generation failed for template {template_id}: {e}")
        await notify_preview_failed(template_id, str(e))


# === Utility Functions ===

def get_connection_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics"""
    return {
        "total_users": len(manager.active_connections),
        "total_gyms": len(manager.gym_connections),
        "template_subscriptions": len(manager.template_connections),
        "background_tasks": len(manager.background_tasks),
        "connections_per_user": {
            str(user_id): len(connections)
            for user_id, connections in manager.active_connections.items()
        }
    }


async def cleanup_background_tasks():
    """Clean up completed background tasks"""
    completed_tasks = []
    
    for task_id, task in manager.background_tasks.items():
        if task.done():
            completed_tasks.append(task_id)
    
    for task_id in completed_tasks:
        del manager.background_tasks[task_id]
        logger.info(f"Cleaned up completed background task: {task_id}")


# Export manager and functions
__all__ = [
    "manager",
    "websocket_endpoint",
    "notify_template_created",
    "notify_template_updated",
    "notify_template_deleted",
    "notify_template_assigned",
    "notify_preview_progress",
    "notify_preview_completed",
    "notify_preview_failed",
    "notify_analytics_update",
    "start_background_preview_generation",
    "get_connection_stats",
    "cleanup_background_tasks"
]
