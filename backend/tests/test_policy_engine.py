import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import Finding
from services.policy_engine import (
    PolicyCondition,
    PolicyConfig,
    PolicyRule,
    evaluate_findings,
)
from services.scanner import run_scan


def make_finding(
    *,
    finding_type: str = "API Key",
    value: str = 'API_KEY = "real-secret-123"',
    severity: str = "HIGH",
) -> Finding:
    return Finding(
        type=finding_type,
        category="SECRET",
        value=value,
        start=0,
        end=len(value),
        line=1,
        severity=severity,
        exact_quote=value,
        source="regex",
    )


def test_policy_block_priority():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.mask",
                detector="api_key",
                severity="critical",
                action="mask",
            ),
            PolicyRule(
                id="secret.api_key.block",
                detector="api_key",
                severity="critical",
                action="block",
            ),
        ]
    )

    result = evaluate_findings([make_finding()], config)

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.policy_decisions[0].policy_action == "block"
    assert result.policy_decisions[0].policy_id == "secret.api_key.block"


def test_policy_mask_when_no_block():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.mask",
                detector="api_key",
                severity="critical",
                action="mask",
            )
        ]
    )

    result = evaluate_findings([make_finding()], config)

    assert result.overall_action == "mask"
    assert result.blocked is False
    assert result.policy_decisions[0].policy_action == "mask"


def test_policy_allow_excludes_masking():
    text = 'API_KEY = "sbx-shared-ab12cd34"'
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="sandbox.api_key.allow",
                detector="api_key",
                severity="critical",
                action="allow",
                condition=PolicyCondition(contains="sbx-shared-"),
            )
        ]
    )

    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=config))

    assert result.overall_action == "allow"
    assert result.findings
    assert "MASKED_API_KEY" not in result.masked_text
    assert "sbx-shared-ab12cd34" in result.masked_text
    assert result.placeholders == []


def test_specific_allow_rule_overrides_generic_block():
    # 이전에는 가장 강한 조치(block)가 항상 이겨서 allow 예외가 절대 적용되지 않았다.
    config = PolicyConfig(
        policies=[
            PolicyRule(id="secret.api_key.block", detector="api_key", severity="critical", action="block"),
            PolicyRule(
                id="sandbox.api_key.allow",
                detector="api_key",
                action="allow",
                condition=PolicyCondition(matches=r"sbx-shared-[a-z0-9]{8}"),
            ),
        ]
    )

    allowed = evaluate_findings([make_finding(value="sbx-shared-ab12cd34")], config)
    blocked = evaluate_findings([make_finding(value="sk-live-real-0011223344")], config)

    assert allowed.overall_action == "allow"
    assert allowed.policy_decisions[0].policy_id == "sandbox.api_key.allow"
    assert blocked.overall_action == "block"


def test_matches_condition_requires_full_match():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="sandbox.api_key.allow",
                detector="api_key",
                action="allow",
                condition=PolicyCondition(matches=r"sbx-shared-[a-z0-9]{8}"),
            ),
        ]
    )

    result = evaluate_findings([make_finding(value="sbx-shared-ab12cd34-and-real-suffix")], config)

    assert result.policy_decisions[0].policy_id is None
    assert result.overall_action == "mask"


def test_priority_overrides_specificity():
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="sandbox.api_key.allow",
                detector="api_key",
                action="allow",
                condition=PolicyCondition(contains="sbx-shared-"),
            ),
            PolicyRule(id="freeze.api_key.block", detector="api_key", action="block", priority=10),
        ]
    )

    result = evaluate_findings([make_finding(value="sbx-shared-ab12cd34")], config)

    assert result.overall_action == "block"
    assert result.policy_decisions[0].policy_id == "freeze.api_key.block"


def test_unmatched_finding_defaults_to_mask():
    text = 'API_KEY = "real-token-123"'
    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=PolicyConfig()))

    assert result.overall_action == "mask"
    assert result.blocked is False
    assert result.masked_text == 'API_KEY = "[MASKED_API_KEY_1]"'


def test_block_response_safe_prompt_is_none():
    text = 'API_KEY = "real-secret-123"'
    config = PolicyConfig(
        policies=[
            PolicyRule(
                id="secret.api_key.block",
                detector="api_key",
                severity="critical",
                action="block",
            )
        ]
    )

    result = asyncio.run(run_scan(text, use_gemma=False, policy_config=config))

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.safe_prompt is None
    assert result.blocked_reason is not None
    assert "real-secret-123" not in result.blocked_reason


def test_existing_response_fields_exist():
    result = asyncio.run(run_scan("hello", use_gemma=False, policy_config=PolicyConfig()))

    assert hasattr(result, "masked_text")
    assert hasattr(result, "safe_prompt")
    assert hasattr(result, "findings")
    assert result.masked_text == "hello"
    assert result.safe_prompt == ""
    assert result.findings == []


def test_default_policy_yaml_blocks_api_key():
    result = asyncio.run(run_scan('API_KEY = "real-token-123"', use_gemma=False))

    assert result.overall_action == "block"
    assert result.blocked is True
    assert result.safe_prompt is None
    assert any(
        decision.policy_id == "secret.api_key.block"
        and decision.policy_action == "block"
        for decision in result.policy_decisions
    )


if __name__ == "__main__":
    test_policy_block_priority()
    test_policy_mask_when_no_block()
    test_policy_allow_excludes_masking()
    test_unmatched_finding_defaults_to_mask()
    test_block_response_safe_prompt_is_none()
    test_existing_response_fields_exist()
    test_default_policy_yaml_blocks_api_key()
    print("policy engine tests passed")
