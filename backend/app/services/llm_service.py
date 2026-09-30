"""Provider-neutral LLM interface for ResearchOps application services."""

from abc import ABC, abstractmethod
from typing import Optional


class LLMService(ABC):
    """Port implemented by Gemini, OpenAI, Anthropic, or local LLM adapters."""

    @abstractmethod
    async def complete(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Return an unmodified text completion for the supplied prompt."""
        raise NotImplementedError
