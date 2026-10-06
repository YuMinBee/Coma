import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_scan import (
    DEFAULT_DATASET,
    TEMPLATE_RE,
    evaluate_case,
    expand_templates,
    load_cases,
)
from services.allowlist import is_placeholder_secret
from services.policy_engine import TYPE_DETECTOR_MAP

KNOWN_DETECTORS = set(TYPE_DETECTOR_MAP.values()) | {"internal_domain"}


def test_eval_dataset_shape():
    cases = load_cases(DEFAULT_DATASET)
    ids = [case.case_id for case in cases]
    categories = {case.category for case in cases}

    assert len(ids) == len(set(ids))
    assert len(cases) >= 130
    assert {
        "benign_prompt",
        "edge_case",
        "internal_info",
        "pii",
        "secrets",
        "korean_pii",
        "secrets_v2",
        "hard_negative",
        "mixed_document",
        "keyword_context",
    } <= categories

    for case in cases:
        assert case.text
        assert "overall_action" in case.expected
        assert not TEMPLATE_RE.search(case.text), case.case_id
        assert case.expected_findings is not None, case.case_id
        for item in case.expected_findings:
            assert item.detector in KNOWN_DETECTORS, (case.case_id, item.detector)
            assert item.value in case.text, (case.case_id, item.value)


def test_blind_holdout_splits_are_well_formed():
    eval_dir = DEFAULT_DATASET.parent
    dev = load_cases(eval_dir / "blind_dev.jsonl")
    test = load_cases(eval_dir / "blind_test.jsonl")
    assert len(dev) + len(test) == 160
    assert not {case.case_id for case in dev} & {case.case_id for case in test}
    for case in [*dev, *test]:
        assert not TEMPLATE_RE.search(case.text), case.case_id
        for item in case.expected_findings or []:
            assert item.detector in KNOWN_DETECTORS, (case.case_id, item.detector)
            assert item.value in case.text, (case.case_id, item.value)


def test_generated_tokens_are_deterministic_and_not_placeholders():
    for name in ("github_token", "openai_key", "slack_token", "google_api_key", "stripe_key", "hf_token"):
        first = expand_templates(f"{{{{gen:{name}}}}}", "case_a")
        assert first == expand_templates(f"{{{{gen:{name}}}}}", "case_a")
        assert first != expand_templates(f"{{{{gen:{name}}}}}", "case_b")
        assert not is_placeholder_secret(first)


def test_known_failures_are_documented():
    cases = load_cases(DEFAULT_DATASET)
    for case in cases:
        if case.known_failure:
            assert len(case.known_failure) > 10


def test_eval_gate_passes():
    # CI 게이트와 같은 조건: 알려진 한계를 뺀 모든 케이스가 기대값과 일치해야 한다.
    cases = [case for case in load_cases(DEFAULT_DATASET) if not case.known_failure]

    async def run_all():
        return [await evaluate_case(case, use_gemma=False, use_gitleaks=False) for case in cases]

    failed = [result.case.case_id for result in asyncio.run(run_all()) if not result.passed]
    assert failed == []


if __name__ == "__main__":
    test_eval_dataset_shape()
    test_generated_tokens_are_deterministic_and_not_placeholders()
    test_known_failures_are_documented()
    test_eval_gate_passes()
    print("eval dataset tests passed")
