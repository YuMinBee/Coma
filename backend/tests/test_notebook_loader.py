import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.regex_scanner import scan_by_regex
from services.masking import apply_masking
from services.notebook_loader import (
    build_masked_notebook,
    build_scan_text,
    enrich_findings_with_cells,
    parse_notebook,
    prepare_notebook_scan,
)
from services.masking import coalesce_span_findings


def _sample_nb():
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"secret": "sk-should-not-scan-metadata"},
        "cells": [
            {
                "cell_type": "code",
                "metadata": {},
                "source": ["API_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"],
                "outputs": [
                    {
                        "output_type": "stream",
                        "text": ["password=leaked-in-output\n"],
                    }
                ],
                "execution_count": 1,
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": "internal notes",
            },
        ],
    }


def test_scan_text_excludes_outputs_and_metadata():
    raw = json.dumps(_sample_nb())
    scan_text, segments = build_scan_text(parse_notebook(raw))
    assert "leaked-in-output" not in scan_text
    assert "sk-should-not-scan-metadata" not in scan_text
    assert "AKIAIOSFODNN7EXAMPLE" in scan_text
    assert len(segments) == 2


def test_enrich_findings_cell_index():
    raw = json.dumps(_sample_nb())
    scan_text, nb, segments = prepare_notebook_scan(raw)
    findings = coalesce_span_findings(scan_by_regex(scan_text))
    enriched = enrich_findings_with_cells(findings, segments, scan_text)
    aws = next(f for f in enriched if "AWS" in f.type or "AKIA" in (f.exact_quote or ""))
    assert aws.cell_index == 0
    assert aws.cell_type == "code"


def test_masked_notebook_masks_source_and_strips_outputs_metadata():
    raw = json.dumps(_sample_nb())
    scan_text, nb, segments = prepare_notebook_scan(raw)
    findings = coalesce_span_findings(scan_by_regex(scan_text))
    enriched = enrich_findings_with_cells(findings, segments, scan_text)
    masked_json = build_masked_notebook(nb, segments, enriched)
    masked_nb = json.loads(masked_json)
    source = "".join(masked_nb["cells"][0]["source"])
    assert "AKIA" not in source
    assert "[MASKED" in source
    assert masked_nb["metadata"] == {}
    assert masked_nb["cells"][0]["metadata"] == {}
    assert masked_nb["cells"][0]["outputs"] == []
    assert masked_nb["cells"][0]["execution_count"] is None
    assert "leaked-in-output" not in masked_json
    assert "sk-should-not-scan-metadata" not in masked_json


if __name__ == "__main__":
    test_scan_text_excludes_outputs_and_metadata()
    test_enrich_findings_cell_index()
    test_masked_notebook_masks_source_and_strips_outputs_metadata()
    print("all notebook tests passed")
