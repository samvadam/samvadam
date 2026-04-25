"""
Abstract base class every voice engine adapter must implement.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator
from ..schemas.unified import UnifiedMessage, SessionConfig


class BaseVoiceEngine(ABC):
    """
    Each voice engine translates between the unified schema and its own wire format.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def connect(self, config: SessionConfig) -> None:
        """Establish connection to the voice engine WebSocket."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the voice engine connection cleanly."""
        ...

    @abstractmethod
    async def send(self, message: UnifiedMessage) -> None:
        """Translate a unified message and send it to the voice engine."""
        ...

    @abstractmethod
    async def receive(self) -> AsyncGenerator[UnifiedMessage, None]:
        """
        Receive raw messages from the voice engine and yield them
        as unified schema messages.
        """
        ...
