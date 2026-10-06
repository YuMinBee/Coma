# SafePromptGuard v5 Eval Report

> Generated: 2026-10-06 09:49 UTC
> Dataset: `backend/eval/dataset.jsonl` (135 cases)
> Gemma: OFF
> Gitleaks: OFF

## Summary

- Case pass rate: 130/135 (96.3%)
- Case pass rate excluding known failures: 130/130 (100.0%)
- Span detectors (micro): precision 1.000 / recall 1.000 / F1 1.000 (TP 80, FP 0, FN 0)
- Cases with a sensitive term left in the output: 0
- Latency avg/p50/p95/max: 0.1ms / 0ms / 0ms / 11ms

## Detector Precision / Recall

Value-level spans from regex/gitleaks detectors. A prediction counts as correct when its
detector matches and its span overlaps the expected value. Keyword rules are line-level
signals and are measured only through the case checks below.

| Detector | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| api_key | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| bank_account | 6 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| business_registration_number | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| corporate_registration_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| credit_card | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| db_url | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| driver_license | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| email | 7 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| foreigner_registration_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_domain | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_ip | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| passport_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| password | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| phone | 11 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| private_key | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| resident_registration_number | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| token | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Check Accuracy

| Check | Accuracy |
|---|---:|
| detected | 130/135 (96.3%) |
| masked | 130/135 (96.3%) |
| blocked | 135/135 (100.0%) |
| safe_prompt_null | 135/135 (100.0%) |
| secret_leakage | 135/135 (100.0%) |
| overall_action | 130/135 (96.3%) |

## Category Pass Rate

| Category | Pass Rate |
|---|---:|
| benign_prompt | 10/10 (100.0%) |
| edge_case | 10/10 (100.0%) |
| hard_negative | 30/30 (100.0%) |
| internal_info | 10/10 (100.0%) |
| keyword_context | 0/5 (0.0%) |
| korean_pii | 30/30 (100.0%) |
| mixed_document | 8/8 (100.0%) |
| pii | 10/10 (100.0%) |
| secrets | 10/10 (100.0%) |
| secrets_v2 | 12/12 (100.0%) |

## Known Limitations

These cases document behavior we have not fixed yet. They stay in the report but
are excluded from the CI gate.

| ID | Pass | Reason |
|---|---:|---|
| kw_admin_001 | no | 키워드 규칙이 내용과 무관하게 해당 줄 전체를 마스킹한다(규칙 재설계 전 알려진 한계). |
| kw_customer_002 | no | 키워드 규칙이 내용과 무관하게 해당 줄 전체를 마스킹한다(규칙 재설계 전 알려진 한계). |
| kw_production_003 | no | 키워드 규칙이 내용과 무관하게 해당 줄 전체를 마스킹한다(규칙 재설계 전 알려진 한계). |
| kw_ranking_004 | no | 키워드 규칙이 내용과 무관하게 해당 줄 전체를 마스킹한다(규칙 재설계 전 알려진 한계). |
| kw_secret_005 | no | 키워드 규칙이 내용과 무관하게 해당 줄 전체를 마스킹한다(규칙 재설계 전 알려진 한계). |

## Cases

| ID | Category | Pass | Action | Findings | Latency | Failed Checks | Detector errors |
|---|---|---:|---|---:|---:|---|---|
| secret_aws_key_001 | secrets | yes | block | 1 | 11ms | - | - |
| secret_api_key_002 | secrets | yes | block | 2 | 0ms | - | - |
| secret_access_key_003 | secrets | yes | block | 1 | 0ms | - | - |
| secret_password_004 | secrets | yes | mask | 1 | 0ms | - | - |
| secret_bearer_005 | secrets | yes | mask | 1 | 0ms | - | - |
| secret_jwt_006 | secrets | yes | mask | 1 | 0ms | - | - |
| secret_private_key_007 | secrets | yes | mask | 1 | 0ms | - | - |
| secret_db_url_008 | secrets | yes | mask | 2 | 0ms | - | - |
| secret_redis_url_009 | secrets | yes | mask | 1 | 0ms | - | - |
| secret_env_file_010 | secrets | yes | mask | 2 | 0ms | - | - |
| pii_email_001 | pii | yes | mask | 1 | 0ms | - | - |
| pii_email_002 | pii | yes | mask | 1 | 0ms | - | - |
| pii_phone_003 | pii | yes | mask | 2 | 0ms | - | - |
| pii_phone_004 | pii | yes | mask | 1 | 0ms | - | - |
| pii_card_005 | pii | yes | mask | 1 | 0ms | - | - |
| pii_card_006 | pii | yes | mask | 1 | 0ms | - | - |
| pii_customer_keyword_007 | pii | yes | mask | 1 | 0ms | - | - |
| pii_client_keyword_008 | pii | yes | mask | 1 | 0ms | - | - |
| pii_payment_keyword_009 | pii | yes | mask | 1 | 0ms | - | - |
| pii_billing_keyword_010 | pii | yes | mask | 1 | 0ms | - | - |
| internal_ip_001 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_ip_002 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_ip_003 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_domain_004 | internal_info | yes | mask | 2 | 0ms | - | - |
| internal_domain_005 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_domain_006 | internal_info | yes | mask | 2 | 0ms | - | - |
| internal_table_007 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_table_008 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_prod_009 | internal_info | yes | mask | 1 | 0ms | - | - |
| internal_admin_010 | internal_info | yes | mask | 1 | 0ms | - | - |
| benign_prompt_001 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_002 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_003 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_004 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_005 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_006 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_007 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_008 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_009 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| benign_prompt_010 | benign_prompt | yes | allow | 0 | 0ms | - | - |
| edge_env_ref_001 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_type_hint_002 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_token_label_003 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_short_bearer_004 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_example_email_005 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_invalid_ip_006 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_settings_ref_007 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_api_key_type_008 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_doc_key_009 | edge_case | yes | allow | 0 | 0ms | - | - |
| edge_fixture_aws_010 | edge_case | yes | allow | 0 | 0ms | - | - |
| kpii_rrn_001 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_rrn_002 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_rrn_003 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_rrn_004 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_foreigner_005 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_foreigner_006 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_corp_007 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_brn_008 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_brn_009 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_account_010 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_account_011 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_account_012 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_account_013 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_passport_014 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_passport_015 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_license_016 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_license_017 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_phone_018 | korean_pii | yes | mask | 2 | 0ms | - | - |
| kpii_phone_019 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_phone_020 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_phone_021 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_email_022 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_email_023 | korean_pii | yes | mask | 1 | 1ms | - | - |
| kpii_card_024 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_card_025 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_card_026 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_password_027 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_password_028 | korean_pii | yes | mask | 1 | 0ms | - | - |
| kpii_mixed_029 | korean_pii | yes | mask | 2 | 0ms | - | - |
| kpii_vpn_ip_030 | korean_pii | yes | mask | 1 | 0ms | - | - |
| sec2_github_001 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_openai_002 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_anthropic_003 | secrets_v2 | yes | block | 2 | 0ms | - | - |
| sec2_slack_004 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_google_005 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_stripe_006 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_hf_007 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_aws_008 | secrets_v2 | yes | block | 1 | 0ms | - | - |
| sec2_privkey_009 | secrets_v2 | yes | mask | 1 | 0ms | - | - |
| sec2_bearer_010 | secrets_v2 | yes | mask | 1 | 0ms | - | - |
| sec2_env_ref_011 | secrets_v2 | yes | allow | 0 | 0ms | - | - |
| sec2_template_012 | secrets_v2 | yes | allow | 0 | 0ms | - | - |
| hneg_001 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_002 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_003 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_004 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_005 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_006 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_007 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_008 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_009 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_010 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_011 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_012 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_013 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_014 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_015 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_016 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_017 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_018 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_019 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_020 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_021 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_022 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_023 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_024 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_025 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_026 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_027 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_028 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_029 | hard_negative | yes | allow | 0 | 0ms | - | - |
| hneg_030 | hard_negative | yes | allow | 0 | 0ms | - | - |
| mixed_cs_ticket_001 | mixed_document | yes | mask | 3 | 0ms | - | - |
| mixed_spring_config_002 | mixed_document | yes | block | 3 | 0ms | - | - |
| mixed_hr_onboarding_003 | mixed_document | yes | mask | 3 | 0ms | - | - |
| mixed_incident_004 | mixed_document | yes | mask | 6 | 0ms | - | - |
| mixed_python_env_005 | mixed_document | yes | allow | 0 | 0ms | - | - |
| mixed_log_006 | mixed_document | yes | mask | 1 | 0ms | - | - |
| mixed_vendor_007 | mixed_document | yes | mask | 3 | 0ms | - | - |
| mixed_readme_008 | mixed_document | yes | allow | 0 | 0ms | - | - |
| kw_admin_001 | keyword_context | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| kw_customer_002 | keyword_context | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| kw_production_003 | keyword_context | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| kw_ranking_004 | keyword_context | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| kw_secret_005 | keyword_context | no | mask | 1 | 0ms | detected, masked, overall_action | - |
