# SafePromptGuard v4.1 Eval Report

> Generated: 2026-06-26 15:01 UTC
> Dataset: `C:/Users/pc/Desktop/safecode_guard/SafePromptGuard_v3/backend/eval/dataset.jsonl`
> Gemma: OFF

## Summary

- Case pass rate: 46/50 (92.0%)
- Latency avg/p50/p95/max: 1.4ms / 1ms / 2ms / 23ms

## Check Accuracy

| Check | Accuracy |
|---|---:|
| detected | 46/50 (92.0%) |
| masked | 46/50 (92.0%) |
| blocked | 48/50 (96.0%) |
| safe_prompt_null | 48/50 (96.0%) |
| secret_leakage | 50/50 (100.0%) |
| overall_action | 46/50 (92.0%) |

## Category Pass Rate

| Category | Pass Rate |
|---|---:|
| benign_prompt | 10/10 (100.0%) |
| edge_case | 6/10 (60.0%) |
| internal_info | 10/10 (100.0%) |
| pii | 10/10 (100.0%) |
| secrets | 10/10 (100.0%) |

## Cases

| ID | Category | Pass | Action | Findings | Latency | Failed Checks |
|---|---|---:|---|---:|---:|---|
| secret_aws_key_001 | secrets | yes | block | 1 | 23ms | - |
| secret_api_key_002 | secrets | yes | block | 2 | 2ms | - |
| secret_access_key_003 | secrets | yes | block | 1 | 1ms | - |
| secret_password_004 | secrets | yes | mask | 1 | 1ms | - |
| secret_bearer_005 | secrets | yes | mask | 1 | 1ms | - |
| secret_jwt_006 | secrets | yes | mask | 1 | 1ms | - |
| secret_private_key_007 | secrets | yes | mask | 3 | 1ms | - |
| secret_db_url_008 | secrets | yes | mask | 2 | 1ms | - |
| secret_redis_url_009 | secrets | yes | mask | 1 | 1ms | - |
| secret_env_file_010 | secrets | yes | mask | 2 | 1ms | - |
| pii_email_001 | pii | yes | mask | 1 | 1ms | - |
| pii_email_002 | pii | yes | mask | 1 | 1ms | - |
| pii_phone_003 | pii | yes | mask | 2 | 1ms | - |
| pii_phone_004 | pii | yes | mask | 1 | 1ms | - |
| pii_card_005 | pii | yes | mask | 1 | 1ms | - |
| pii_card_006 | pii | yes | mask | 1 | 1ms | - |
| pii_customer_keyword_007 | pii | yes | mask | 1 | 1ms | - |
| pii_client_keyword_008 | pii | yes | mask | 1 | 1ms | - |
| pii_payment_keyword_009 | pii | yes | mask | 1 | 1ms | - |
| pii_billing_keyword_010 | pii | yes | mask | 1 | 1ms | - |
| internal_ip_001 | internal_info | yes | mask | 1 | 1ms | - |
| internal_ip_002 | internal_info | yes | mask | 1 | 1ms | - |
| internal_ip_003 | internal_info | yes | mask | 1 | 1ms | - |
| internal_domain_004 | internal_info | yes | mask | 2 | 1ms | - |
| internal_domain_005 | internal_info | yes | mask | 1 | 1ms | - |
| internal_domain_006 | internal_info | yes | mask | 2 | 2ms | - |
| internal_table_007 | internal_info | yes | mask | 1 | 1ms | - |
| internal_table_008 | internal_info | yes | mask | 1 | 2ms | - |
| internal_prod_009 | internal_info | yes | mask | 1 | 8ms | - |
| internal_admin_010 | internal_info | yes | mask | 1 | 2ms | - |
| benign_prompt_001 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_002 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_003 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_004 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_005 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_006 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_007 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_008 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_009 | benign_prompt | yes | allow | 0 | 0ms | - |
| benign_prompt_010 | benign_prompt | yes | allow | 0 | 0ms | - |
| edge_env_ref_001 | edge_case | yes | allow | 0 | 0ms | - |
| edge_type_hint_002 | edge_case | yes | allow | 0 | 0ms | - |
| edge_token_label_003 | edge_case | yes | allow | 0 | 0ms | - |
| edge_short_bearer_004 | edge_case | yes | allow | 0 | 0ms | - |
| edge_example_email_005 | edge_case | no | mask | 1 | 2ms | detected, masked, overall_action |
| edge_invalid_ip_006 | edge_case | no | mask | 2 | 1ms | detected, masked, overall_action |
| edge_settings_ref_007 | edge_case | yes | allow | 0 | 0ms | - |
| edge_api_key_type_008 | edge_case | yes | allow | 0 | 0ms | - |
| edge_doc_key_009 | edge_case | no | block | 1 | 1ms | detected, masked, blocked, safe_prompt_null, overall_action |
| edge_fixture_aws_010 | edge_case | no | block | 1 | 1ms | detected, masked, blocked, safe_prompt_null, overall_action |
