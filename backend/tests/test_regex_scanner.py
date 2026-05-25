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


def test_env_secret_names_are_not_reported_as_values():
    text = """
API_KEY = os.getenv("API_KEY")
DB_PASSWORD = os.getenv("DB_PASSWORD")
def hash_password(password: str):
    return password
"""
    findings = scan_by_regex(text)
    assert findings == []


def test_literal_secret_values_are_still_detected():
    text = """
API_KEY = "sk-test-1234567890abcdef1234567890abcdef"
DB_PASSWORD = "admin1234"
"""
    findings = scan_by_regex(text)
    assert any(f.type == "API Key" for f in findings)
    assert any(f.type == "Password" for f in findings)


if __name__ == "__main__":
    test_internal_domain_detected()
    test_long_plain_ascii_has_no_regex_findings()
    test_env_secret_names_are_not_reported_as_values()
    test_literal_secret_values_are_still_detected()
    print("regex scanner tests passed")
