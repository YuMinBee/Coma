from pydantic import BaseModel, Field
from typing import Literal

from constants import MAX_TEXT_CHARS


class ScanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_CHARS)
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
    cell_index: int | None = None
    cell_type: str | None = None


class ScanLogEntry(BaseModel):
    id: int
    created_at: str
    input_kind: Literal["text", "file"]
    filename: str | None = None
    source_kind: Literal["text", "notebook"]
    risk_level: Literal["높음", "중간", "낮음"]
    risk_score: int
    findings_count: int
    gemma_used: bool
    duration_ms: int
    text_length: int


class ScanLogListResponse(BaseModel):
    items: list[ScanLogEntry]
    db_path: str


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
    source_kind: Literal["text", "notebook"] = "text"
    masked_notebook_json: str | None = None
    notebook_cell_count: int | None = None
