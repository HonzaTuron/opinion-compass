"""This module defines Pydantic models for this project.

These models are used mainly for the structured tool and LLM outputs.
Resources:
- https://docs.pydantic.dev/latest/concepts/models/
"""

from __future__ import annotations

from pydantic import BaseModel


class AgentStructuredOutput(BaseModel):
    """Structured output for the ReAct agent.
    Returned as a structured output by the ReAct agent.
    """

    evidences: list[Evidence]


class Evidence(BaseModel):
    """Represents evidence relating to a claim of particular person."""
    url: str
    text: str
    source: str
