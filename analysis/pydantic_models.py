from typing import List
from pydantic import BaseModel, Field

# Define Pydantic models for parsing
class QuestionAnswerableResult(BaseModel):
    REASONING: str = Field(description="Reasoning for the score")
    SCORE: str = Field(description="PASS or FAIL")

class ClaimVerifiableResult(BaseModel):
    CHECKWORTHY: str = Field(description="PASS or FAIL")

class HallucinationResult(BaseModel):
    REASONING: List[str] = Field(description="Reasoning for the score")
    SCORE: str = Field(description="PASS or FAIL")

class FactCheckResult(BaseModel):
    REASONING: List[str] = Field(description="Reasoning for the score")
    SCORE: str = Field(description="PASS or FAIL")

class DDGInput(BaseModel):
    """Input for the DuckDuckGo search tool."""
    query: str = Field(description="search query to look up")
