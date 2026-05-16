from pydantic import BaseModel, Field
from typing import Literal


class ScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500_000)
    use_gemma: bool = True


class Finding(BaseModel):
    type: str
    category: str
    value: str
    start: int | None = None
    end: int | None = None
    line: int | None = None
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    exact_quote: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None
    action: str | None = None
    source: Literal["regex", "rule", "gemma"]


class ScanResponse(BaseModel):
    risk_level: Literal["높음", "중간", "낮음"]
    risk_score: int
    findings: list[Finding]
    detected_items: list[str]
    recommendations: list[str]
    masked_text: str
    safe_prompt: str
    gemma_available: bool
    gemma_used: bool
