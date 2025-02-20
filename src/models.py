"""This module defines Pydantic models for this project.

These models are used mainly for the structured tool and LLM outputs.
Resources:
- https://docs.pydantic.dev/latest/concepts/models/
"""

from __future__ import annotations
from typing import Annotated

from pydantic import BaseModel, Field


class SocialMediaHandle(BaseModel):
    socialMedia: str
    handle: str

class SocialMediaHandles(BaseModel):
    handles: list[SocialMediaHandle]

class RawEvidence(BaseModel):
    """Represents evidence relating to a claim of particular person."""
    url: str
    text: str
    source: str

class RawEvidenceList(BaseModel):
    """List of evidence."""
    evidences: list[RawEvidence]

class Evidence(RawEvidence):
    """Represents evidence relating to a claim of particular person with a score."""
    score: float # Score from 0 to 1 where 1 pro-western and 0 means anti-western
    relevance: float # Relevance score from 0 to 1 where 1 is highly relevant and 0 is not relevant at all

class EvidenceList(BaseModel):
    """List of evidence with scores."""
    evidences: list[Evidence]

class AgentStructuredOutput(EvidenceList):
    """Structured output for the ReAct agent.
    Returned as a structured output by the ReAct agent.
    """

    pass