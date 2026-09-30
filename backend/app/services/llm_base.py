"""Provider-agnostic LLM service interface.

Defines the contract for LLM providers (Gemini, OpenAI, Anthropic, local)
ensuring the agentic system remains completely vendor-agnostic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMService(ABC):
    """Abstract interface for pluggable LLM provider services."""

    def __init__(self, model_name: str, temperature: float = 0.2, **kwargs: Any) -> None:
        self.model_name = model_name
        self.temperature = temperature
        self.extra_kwargs = kwargs

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Generate freeform textual completion."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> T:
        """Generate structured output validated against a Pydantic schema."""
        pass

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        """Generate vector embeddings for semantic search."""
        pass
