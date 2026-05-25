import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gemma_analyzer import _is_secret_reference_quote


def test_env_secret_references_are_filtered():
    assert _is_secret_reference_quote('API_KEY = os.getenv("API_KEY")')
    assert _is_secret_reference_quote('DB_PASSWORD = os.getenv("DB_PASSWORD")')


def test_type_hints_are_filtered():
    assert _is_secret_reference_quote("def hash_password(password: str):")


def test_literal_secret_values_are_not_filtered():
    assert not _is_secret_reference_quote('API_KEY = "sk-test-1234567890abcdef1234567890abcdef"')
    assert not _is_secret_reference_quote('DB_PASSWORD = "admin1234"')


if __name__ == "__main__":
    test_env_secret_references_are_filtered()
    test_type_hints_are_filtered()
    test_literal_secret_values_are_not_filtered()
    print("gemma filter tests passed")
