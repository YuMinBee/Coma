import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.schemas import Finding
from services import scanner
from services.gitleaks_scanner import (
    findings_from_gitleaks_report,
    scan_with_gitleaks,
)
from services.policy_engine import PolicyConfig, PolicyRule


def test_gitleaks_report_maps_to_finding():
    text = 'token = "sk-live-1234567890abcdef"'
    report = [
        {
            "RuleID": "generic-api-key",
            "Description": "Generic API Key",
            "Secret": "sk-live-1234567890abcdef",
            "Match": 'token = "sk-live-1234567890abcdef"',
            "StartLine": 1,
            "StartColumn": 10,
        }
    ]

    findings = findings_from_gitleaks_report(report, text)

    assert len(findings) == 1
    assert findings[0].source == "gitleaks"
    assert findings[0].detector == "api_key"
    assert findings[0].type == "API Key"
    assert findings[0].exact_quote == "sk-live-1234567890abcdef"
    assert findings[0].start == text.index("sk-live")


def test_gitleaks_unavailable_returns_empty():
    findings = scan_with_gitleaks(
        'token = "sk-live-1234567890abcdef"',
        command="definitely-not-installed-gitleaks",
    )

    assert findings == []


def test_scanner_treats_gitleaks_as_detector():
    original_available = scanner.gitleaks_available
    original_scan = scanner.scan_with_gitleaks

    def fake_available():
        return True

    def fake_scan(text, *, filename=None):
        quote = "external-secret-value"
        return [
            Finding(
                type="API Key",
                category="SECRET",
                value=quote,
                start=text.index(quote),
                end=text.index(quote) + len(quote),
                line=1,
                severity="HIGH",
                detector="api_key",
                exact_quote=quote,
                source="gitleaks",
            )
        ]

    scanner.gitleaks_available = fake_available
    scanner.scan_with_gitleaks = fake_scan
    try:
        result = asyncio.run(
            scanner.run_scan(
                "plain text external-secret-value",
                use_gemma=False,
                use_gitleaks=True,
                policy_config=PolicyConfig(
                    policies=[
                        PolicyRule(
                            id="secret.api_key.block",
                            detector="api_key",
                            severity="critical",
                            action="block",
                        )
                    ]
                ),
            )
        )
    finally:
        scanner.gitleaks_available = original_available
        scanner.scan_with_gitleaks = original_scan

    assert result.gitleaks_available is True
    assert result.gitleaks_used is True
    assert result.overall_action == "block"
    assert result.safe_prompt is None
    assert result.findings[0].source == "gitleaks"
    assert "external-secret-value" not in result.masked_text


if __name__ == "__main__":
    test_gitleaks_report_maps_to_finding()
    test_gitleaks_unavailable_returns_empty()
    test_scanner_treats_gitleaks_as_detector()
    print("gitleaks scanner tests passed")
