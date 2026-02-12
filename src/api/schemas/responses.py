"""
Standard API response wrappers.

Provides consistent response shapes across all endpoints.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    """Standard success response wrapper."""
    success: bool = True
    data: Any = None
    message: str = ""
    timestamp: datetime = None
    
    def __init__(self, **kwargs):
        if "timestamp" not in kwargs or kwargs["timestamp"] is None:
            kwargs["timestamp"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: str
    detail: str = ""
    timestamp: datetime = None
    
    def __init__(self, **kwargs):
        if "timestamp" not in kwargs or kwargs["timestamp"] is None:
            kwargs["timestamp"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)
