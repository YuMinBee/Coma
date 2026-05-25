import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.rule_scanner import scan_by_rules


def test_plain_user_id_is_not_internal_table():
    findings = scan_by_rules("def get_user(user_id: int):\n    return user_id\n", "example.py")
    assert findings == []


def test_domain_table_names_are_still_detected():
    findings = scan_by_rules(
        "CREATE TABLE customer_payment_tokens (id INTEGER PRIMARY KEY);",
        "schema.sql",
    )
    assert any(f.category == "INFRA_INFO" for f in findings)


if __name__ == "__main__":
    test_plain_user_id_is_not_internal_table()
    test_domain_table_names_are_still_detected()
    print("rule scanner tests passed")
