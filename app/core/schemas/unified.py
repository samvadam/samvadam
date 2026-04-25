"""
Unified schema for all voice engine providers.
This is the single schema our client always speaks.
"""


from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# Enums

class VoiceEngine(str, Enum):
    ULTRAVOX = "ultravox"
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"


class MessageType(str, Enum):
    # Client -> Server
    SESSION_START = "session.start"
    AUDIO_CHUNK = "audio.chunk"
    USER_TEXT = "user.text"
    TOOL_RESULT = "tool.result"
    CONTEXT_UPDATE = "context.update"
    HANG_UP = "hang_up"
    PING = "ping"
    PONG = "pong"

    # Server → Client
    SESSION_READY = "session.ready"
    TRANSCRIPT = "transcript"
    AGENT_RESPONSE = "agent.response"
    AUDIO_RESPONSE = "audio.response"
    TOOL_CALL = "tool.call"
    STATE = "state"
    ERROR = "error"


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class TranscriptRole(str, Enum):
    USER = "user"
    AGENT = "agent"


class Urgency(str, Enum):
    IMMEDIATE = "immediate"
    SOON = "soon"
    LATER = "later"


# Base


class UnifiedMessage(BaseModel):
    type: MessageType


# Samvadam → Voice-Engine messages

class AgentConfig(BaseModel):
    agent_id: str
    prompt: Optional[str] = None
    first_message: Optional[str] = None
    language: Optional[str] = None
    voice_id: Optional[str] = None


class SessionConfig(BaseModel):
    agent: Optional[AgentConfig] = None
    dynamic_vars: Optional[dict[str, Any]] = None
    extra: Optional[dict[str, Any]] = None  # telephony-specific passthrough


class SessionStart(UnifiedMessage):
    """Client initiates a session with config."""
    type: MessageType = MessageType.SESSION_START
    voice_engine: VoiceEngine
    session_id: str
    session_config: SessionConfig = Field(default_factory=SessionConfig)


class AudioChunk(UnifiedMessage):
    """Client streams audio to the server."""
    type: MessageType = MessageType.AUDIO_CHUNK
    audio: str  # base64-encoded audio data


class UserText(UnifiedMessage):
    """Client sends a text message as the user."""
    type: MessageType = MessageType.USER_TEXT
    text: str
    urgency: Urgency = Urgency.SOON


class ToolResult(UnifiedMessage):
    """Client returns the result of a tool invocation."""
    type: MessageType = MessageType.TOOL_RESULT
    tool_name: str
    tool_call_id: str
    result: str
    is_error: bool = False


class ContextUpdate(UnifiedMessage):
    """Silent context injected into the agent (e.g. 'user opened pricing page')."""
    type: MessageType = MessageType.CONTEXT_UPDATE
    text: str


class HangUp(UnifiedMessage):
    """Client requests the call to end."""
    type: MessageType = MessageType.HANG_UP
    message: Optional[str] = None


class Ping(UnifiedMessage):
    type: MessageType = MessageType.PING
    timestamp: float


# Voice-Engine → Samvadam messages


class SessionReady(UnifiedMessage):
    """Server confirms session is live."""
    type: MessageType = MessageType.SESSION_READY
    session_id: str
    voice_engine: VoiceEngine
    audio_format: Optional[str] = None


class Transcript(UnifiedMessage):
    """A transcript chunk from user or agent."""
    type: MessageType = MessageType.TRANSCRIPT
    role: TranscriptRole
    text: str
    is_final: bool = False
    ordinal: Optional[int] = None


class AgentResponse(UnifiedMessage):
    """Full agent text response."""
    type: MessageType = MessageType.AGENT_RESPONSE
    text: str
    is_final: bool = True


class AudioResponse(UnifiedMessage):
    """Agent audio response chunk."""
    type: MessageType = MessageType.AUDIO_RESPONSE
    audio: str     # base64
    event_id: Optional[int] = None


class ToolCall(UnifiedMessage):
    """Server asks client to invoke a tool."""
    type: MessageType = MessageType.TOOL_CALL
    tool_call_id: str
    tool_name: str
    parameters: dict[str, Any]


class StateUpdate(UnifiedMessage):
    """Agent state changed."""
    type: MessageType = MessageType.STATE
    state: AgentState


class ErrorMessage(UnifiedMessage):
    """Something went wrong."""
    type: MessageType = MessageType.ERROR
    message: str
    code: Optional[str] = None


class Pong(UnifiedMessage):
    type: MessageType = MessageType.PONG
    timestamp: float
