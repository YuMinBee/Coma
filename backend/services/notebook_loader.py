"""Jupyter .ipynb — 입력 셀 source 검사·마스킹, outputs/metadata 제거."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass

from models.schemas import Finding
from services.masking import apply_masking

SCANNABLE_CELL_TYPES = frozenset({"code", "markdown", "raw"})


class NotebookParseError(ValueError):
    pass


@dataclass
class CellSegment:
    cell_index: int
    cell_type: str
    global_start: int
    global_end: int
    source_start: int
    source_end: int
    source: str
    source_was_list: bool


def _normalize_source(source: str | list[str] | None) -> tuple[str, bool]:
    if source is None:
        return "", False
    if isinstance(source, list):
        return "".join(source), True
    return str(source), False


def _write_cell_source(cell: dict, text: str, was_list: bool) -> None:
    if was_list:
        if not text:
            cell["source"] = []
            return
        lines = text.splitlines(keepends=True)
        if text and not text.endswith("\n") and lines:
            if not lines[-1].endswith("\n"):
                pass
        cell["source"] = lines if lines else [""]
    else:
        cell["source"] = text


def parse_notebook(raw: str) -> dict:
    try:
        nb = json.loads(raw)
    except json.JSONDecodeError as e:
        raise NotebookParseError(f"노트북 JSON 형식이 올바르지 않습니다: {e}") from e

    if not isinstance(nb, dict) or "cells" not in nb:
        raise NotebookParseError("nbformat 구조가 아닙니다. cells 배열이 필요합니다.")
    if not isinstance(nb.get("cells"), list):
        raise NotebookParseError("cells가 배열이 아닙니다.")

    return nb


def build_scan_text(nb: dict) -> tuple[str, list[CellSegment]]:
    """code/markdown/raw 셀의 source만 합쳐 검사용 텍스트를 만든다."""
    parts: list[str] = []
    segments: list[CellSegment] = []
    pos = 0

    for cell_index, cell in enumerate(nb["cells"]):
        if not isinstance(cell, dict):
            continue
        cell_type = cell.get("cell_type", "")
        if cell_type not in SCANNABLE_CELL_TYPES:
            continue

        source, was_list = _normalize_source(cell.get("source"))
        if not source.strip():
            continue
        header = f"# [Cell {cell_index + 1} · {cell_type}]\n"
        prefix = "\n" if parts else ""
        chunk = prefix + header + source

        global_start = pos + len(prefix)
        source_start = global_start + len(header)
        source_end = source_start + len(source)
        global_end = source_end

        segments.append(
            CellSegment(
                cell_index=cell_index,
                cell_type=cell_type,
                global_start=global_start,
                global_end=global_end,
                source_start=source_start,
                source_end=source_end,
                source=source,
                source_was_list=was_list,
            )
        )
        parts.append(chunk)
        pos = global_end

    scan_text = "".join(parts)
    if not scan_text.strip():
        raise NotebookParseError("검사할 셀 내용이 없습니다. code/markdown/raw 셀에 내용을 추가하세요.")

    return scan_text, segments


def prepare_notebook_scan(raw: str) -> tuple[str, dict, list[CellSegment]]:
    nb = parse_notebook(raw)
    scan_text, segments = build_scan_text(nb)
    return scan_text, nb, segments


def _segment_for_position(segments: list[CellSegment], pos: int) -> CellSegment | None:
    for seg in segments:
        if seg.source_start <= pos < seg.source_end:
            return seg
        if seg.global_start <= pos < seg.global_end:
            return seg
    return None


def _line_start_offsets(scan_text: str) -> list[int]:
    offsets: list[int] = []
    pos = 0
    for line in scan_text.splitlines(keepends=True):
        offsets.append(pos)
        pos += len(line)
    if not offsets and scan_text:
        offsets.append(0)
    return offsets


def enrich_findings_with_cells(
    findings: list[Finding],
    segments: list[CellSegment],
    scan_text: str,
) -> list[Finding]:
    line_offsets = _line_start_offsets(scan_text)
    enriched: list[Finding] = []

    for f in findings:
        updates: dict = {}

        if f.start is not None:
            seg = _segment_for_position(segments, f.start)
            if seg:
                updates["cell_index"] = seg.cell_index
                updates["cell_type"] = seg.cell_type
                if f.start >= seg.source_start:
                    local_pos = f.start - seg.source_start
                    updates["line"] = seg.source[:local_pos].count("\n") + 1
        elif f.line is not None and 1 <= f.line <= len(line_offsets):
            pos = line_offsets[f.line - 1]
            seg = _segment_for_position(segments, pos)
            if seg:
                updates["cell_index"] = seg.cell_index
                updates["cell_type"] = seg.cell_type
                if pos >= seg.source_start:
                    updates["line"] = seg.source[: pos - seg.source_start].count("\n") + 1

        enriched.append(f.model_copy(update=updates) if updates else f)

    return enriched


def _findings_for_cell_source(
    findings: list[Finding], seg: CellSegment
) -> list[Finding]:
    local: list[Finding] = []
    for f in findings:
        if f.start is not None and f.end is not None:
            if f.start >= seg.source_start and f.end <= seg.source_end:
                local.append(
                    f.model_copy(
                        update={
                            "start": f.start - seg.source_start,
                            "end": f.end - seg.source_start,
                            "line": None,
                        }
                    )
                )
            elif f.start < seg.source_end and f.end > seg.source_start:
                overlap_start = max(f.start, seg.source_start)
                overlap_end = min(f.end, seg.source_end)
                if overlap_start < overlap_end:
                    local.append(
                        f.model_copy(
                            update={
                                "start": overlap_start - seg.source_start,
                                "end": overlap_end - seg.source_start,
                                "line": None,
                            }
                        )
                    )
        elif f.cell_index == seg.cell_index and f.line is not None:
            local.append(f.model_copy(update={"start": None, "end": None}))
    return local


def build_masked_notebook(nb: dict, segments: list[CellSegment], findings: list[Finding]) -> str:
    nb_out = copy.deepcopy(nb)
    nb_out["metadata"] = {}
    for seg in segments:
        cell_findings = _findings_for_cell_source(findings, seg)
        masked_source = apply_masking(seg.source, cell_findings)
        cell = nb_out["cells"][seg.cell_index]
        _write_cell_source(cell, masked_source, seg.source_was_list)
    for cell in nb_out.get("cells", []):
        if not isinstance(cell, dict):
            continue
        cell["metadata"] = {}
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    return json.dumps(nb_out, ensure_ascii=False, indent=1)
