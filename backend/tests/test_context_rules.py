"""블라인드 평가셋(dev 절반) 분석에서 나온 규칙들의 회귀 테스트."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import validators
from services.allowlist import is_placeholder_secret
from services.masking import apply_masking
from services.regex_scanner import scan_by_regex
from services.scanner import run_scan


def detected(text: str) -> list[tuple[str, str]]:
    return [(f.type, f.exact_quote) for f in scan_by_regex(text)]


def test_csv_header_names_the_column():
    card = "4000123456789011"
    assert not validators.luhn_valid(card)
    text = f"거래ID,금액,카드번호,승인시각\nTX-1,129000,{card},2026-10-05 20:14:03"
    assert ("Credit Card", card) in detected(text)


def test_csv_header_alone_is_not_a_label_for_other_columns():
    text = "거래ID,금액,카드번호\n4000123456789011,129000,1111"
    assert detected(text) == []


def test_sql_insert_column_list_names_the_value():
    text = (
        "INSERT INTO vendors (name, brn, contact_phone)\n"
        "VALUES ('그린필드', '617-81-20585', '031-215-9980');"
    )
    assert ("Business Registration Number", "617-81-20585") in detected(text)
    assert ("Phone", "031-215-9980") in detected(text)


def test_account_labeled_by_bank_name_or_following_keyword():
    assert detected("국민 817201-01-224514 계좌 맞지?") == [("Bank Account", "817201-01-224514")]
    assert detected("우리은행: 1002-345-678902") == [("Bank Account", "1002-345-678902")]
    assert detected("송장 817201-01-224514, 계좌 변경 문의") == []


def test_placeholder_words_must_look_human_written():
    assert not is_placeholder_secret("wJalrUqExAmPLE/K7MDENGbPxRfiCYzQ3nFx")
    assert is_placeholder_secret("CHANGE_ME")
    assert is_placeholder_secret("change-me-before-prod")
    assert is_placeholder_secret("ExampleKey123")


def test_provider_key_inside_bearer_header_is_blocked():
    key = "sk-proj-" + "Ab3dE5gH7jK9mN1pQ3sT5vX7zA9cE1gI_kM3"
    result = asyncio.run(run_scan(f'"Authorization": "Bearer {key}"', use_gemma=False, use_gitleaks=False))
    assert [f.type for f in result.findings] == ["OpenAI API Key"]
    assert result.overall_action == "block"


def test_oracle_thin_jdbc_url_covers_the_ip_inside():
    text = 'String url = "jdbc:oracle:thin:@192.168.0.14:1521/ORCLPDB1";'
    result = asyncio.run(run_scan(text, use_gemma=False, use_gitleaks=False))
    assert [f.type for f in result.findings] == ["DB URL"]
    assert "192.168.0.14" not in result.masked_text


def test_setter_calls_with_secret_literals():
    assert detected('cfg.setPassword("0raclePw#77");') == [("Password", "0raclePw#77")]
    assert detected('client.withApiKey("live-7f3k2m9q1x");') == [("API Key", "live-7f3k2m9q1x")]
    assert detected('String p = props.getPassword("user");') == []
    assert detected('print("password reset done")') == []


def test_short_password_keys():
    assert detected('"smtp": { "user": "noreply", "pass": "mailer$4471" }') == [("Password", "mailer$4471")]
    assert detected("DB_PW=s3cret!pw") == [("Password", "s3cret!pw")]
    assert detected("bypass=true") == []
    assert detected("use_ssl_pass=false") == []


def test_client_secret_is_an_api_credential():
    assert detected('CLIENT_SECRET = "cs_7hN2pQ9rvB3kLd0B"') == [("API Key", "cs_7hN2pQ9rvB3kLd0B")]


def test_private_key_header_mention_in_code_masks_only_the_header():
    text = 'assert pem.startsWith("-----BEGIN RSA PRIVATE KEY-----");\nnext_step()'
    masked = apply_masking(text, scan_by_regex(text))
    assert masked == 'assert pem.startsWith("[MASKED_PRIVATE_KEY]");\nnext_step()'


def test_bearer_token_as_config_key():
    token = "b1vf_FE-FhpMODTgoo8bPYYFqTMTiTMK-DsHtipX"
    assert detected(f"auth:\n  bearer: {token}") == [("Bearer Token", token)]
