"""Unit tests for LLM-backed research planning with mock providers."""

import pytest

from backend.app.services.llm_service import LLMService
from backend.app.services.research_planner import ResearchPlanner, ResearchPlannerError


class MockLLMService(LLMService):
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    async def complete(self, prompt, system_instruction=None):
        self.calls += 1
        return next(self.responses)


@pytest.mark.asyncio
async def test_planner_extracts_validated_healthcare_research_plan():
    llm = MockLLMService([
        '''{
            "objective": "Analyze cardiac healthcare infrastructure and identify service gaps.",
            "location": "Whitefield",
            "radius_km": 10,
            "service": "cardiology",
            "required_entities": ["facilities", "cardiology services", "competitors"],
            "tasks": [
                {"task_type": "facility discovery", "description": "Find facilities within the stated area.", "required_evidence": ["official facility registries"]},
                {"task_type": "service-gap analysis", "description": "Compare cardiac service coverage.", "required_evidence": ["service directories"]},
                {"task_type": "source verification", "description": "Verify findings with authoritative sources.", "required_evidence": ["government or provider records"]}
            ],
            "required_evidence": ["official facility registries", "service directories"],
            "missing_information": []
        }'''
    ])

    plan = await ResearchPlanner(llm).plan(
        "Analyze cardiac healthcare infrastructure within 10 km of Whitefield and identify potential service gaps."
    )

    assert plan.location == "Whitefield"
    assert plan.radius_km == 10
    assert plan.service == "cardiology"
    assert [task.task_type for task in plan.tasks] == ["facility discovery", "service-gap analysis", "source verification"]


@pytest.mark.asyncio
async def test_planner_retries_malformed_llm_output():
    llm = MockLLMService([
        "not JSON",
        '''{"objective":"Assess facilities","location":null,"radius_km":null,"service":null,"required_entities":[],"tasks":[{"task_type":"facility discovery","description":"Find facilities.","required_evidence":[]}],"required_evidence":[],"missing_information":["location"]}''',
    ])

    plan = await ResearchPlanner(llm).plan("Assess local healthcare infrastructure")

    assert llm.calls == 2
    assert plan.location is None
    assert plan.missing_information == ["location"]


@pytest.mark.asyncio
async def test_planner_returns_meaningful_error_after_invalid_retries():
    llm = MockLLMService(["[]", "still not JSON"])

    with pytest.raises(ResearchPlannerError, match="invalid research plan after 2 attempts"):
        await ResearchPlanner(llm).plan("Assess cardiac infrastructure")
