import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.regex_scanner import scan_by_regex


def test_internal_domain_detected():
    findings = scan_by_regex("spring.datasource.url=jdbc:mysql://prod-db.company.internal:3306/app")
    assert any(f.type == "Internal Domain" and f.exact_quote == "prod-db.company.internal" for f in findings)


def test_long_plain_ascii_has_no_regex_findings():
    findings = scan_by_regex("A" * 1_048_576)
    assert findings == []


if __name__ == "__main__":
    test_internal_domain_detected()
    test_long_plain_ascii_has_no_regex_findings()
    print("regex scanner tests passed")
