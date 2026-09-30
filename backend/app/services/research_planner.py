"""LLM-backed, provider-independent research task planner."""

import json
from typing import Optional

from pydantic import ValidationError

from backend.app.prompts.research_planner import RESEARCH_PLANNER_PROMPT, RESEARCH_PLANNER_SYSTEM_PROMPT
from backend.app.schemas.planner import ResearchPlan
from backend.app.services.llm_service import LLMService


class ResearchPlannerError(Exception):
    """Raised when an LLM cannot produce a valid research plan."""


class ResearchPlanner:
    """Extract and validate a research plan through an injected LLM provider."""

    def __init__(self, llm_service: LLMService, max_attempts: int = 2) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.llm_service = llm_service
        self.max_attempts = max_attempts

    async def plan(self, query: str) -> ResearchPlan:
        """Generate a validated plan, retrying malformed model output once by default."""
        if not query or not query.strip():
            raise ValueError("A non-empty research query is required.")

        prompt = RESEARCH_PLANNER_PROMPT.format(query=query.strip())
        last_error: Optional[Exception] = None
        for attempt in range(self.max_attempts):
            retry_instruction = None
            if attempt:
                retry_instruction = (
                    "Your previous response was malformed. Return only a complete JSON object "
                    "that matches the requested schema."
                )
            try:
                response = await self.llm_service.complete(
                    prompt,
                    system_instruction=retry_instruction or RESEARCH_PLANNER_SYSTEM_PROMPT,
                )
                return self._validate_response(response)
            except (json.JSONDecodeError, ValidationError, TypeError) as exc:
                last_error = exc

        raise ResearchPlannerError(
            f"The language model returned an invalid research plan after {self.max_attempts} attempts."
        ) from last_error

    @staticmethod
    def _validate_response(response: str) -> ResearchPlan:
        """Parse JSON and enforce the public plan contract."""
        if not isinstance(response, str):
            raise TypeError("LLM response must be a JSON string.")
        return ResearchPlan.model_validate(json.loads(response))
