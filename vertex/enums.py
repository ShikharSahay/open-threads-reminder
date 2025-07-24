from enum import Enum

class ThreadState(Enum):
    """Enum for different thread states"""
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    CHIT_CHAT = "chit_chat"
    UNKNOWN = "unknown"

class ReminderAction(Enum):
    """Enum for reminder actions"""
    SEND_REMINDER = "send_reminder"
    NO_REMINDER = "no_reminder"

class ThreadPriority(Enum):
    """Enum for thread priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none" 