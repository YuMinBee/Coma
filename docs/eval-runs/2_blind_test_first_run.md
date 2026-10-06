# SafePromptGuard v5 Eval Report

> Generated: 2026-10-06 09:44 UTC
> Dataset: `backend/eval/blind_test.jsonl` (77 cases)
> Gemma: OFF
> Gitleaks: OFF

## Summary

- Case pass rate: 74/77 (96.1%)
- Case pass rate excluding known failures: 74/77 (96.1%)
- Span detectors (micro): precision 0.990 / recall 0.990 / F1 0.990 (TP 95, FP 1, FN 1)
- Cases with a sensitive term left in the output: 1
- Latency avg/p50/p95/max: 0.1ms / 0ms / 0ms / 11ms

## Detector Precision / Recall

Value-level spans from regex/gitleaks detectors. A prediction counts as correct when its
detector matches and its span overlaps the expected value. Keyword rules are line-level
signals and are measured only through the case checks below.

| Detector | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| api_key | 17 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| bank_account | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| business_registration_number | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| corporate_registration_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| credit_card | 5 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| db_url | 7 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| driver_license | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| email | 13 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| foreigner_registration_number | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_domain | 4 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| internal_ip | 8 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| passport_number | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| password | 6 | 1 | 0 | 0.857 | 1.000 | 0.923 |
| phone | 15 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| private_key | 1 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| resident_registration_number | 2 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| token | 4 | 0 | 1 | 1.000 | 0.800 | 0.889 |

## Check Accuracy

| Check | Accuracy |
|---|---:|
| detected | 25/27 (92.6%) |
| masked | 75/77 (97.4%) |
| blocked | 77/77 (100.0%) |
| safe_prompt_null | 77/77 (100.0%) |
| secret_leakage | 76/77 (98.7%) |
| overall_action | 75/77 (97.4%) |

## Category Pass Rate

| Category | Pass Rate |
|---|---:|
| blind_test | 74/77 (96.1%) |

## Cases

| ID | Category | Pass | Action | Findings | Latency | Failed Checks | Detector errors |
|---|---|---:|---|---:|---:|---|---|
| blind_007 | blind_test | yes | mask | 2 | 11ms | - | - |
| blind_008 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_009 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_011 | blind_test | yes | block | 1 | 0ms | - | - |
| blind_012 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_014 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_016 | blind_test | yes | block | 2 | 0ms | - | - |
| blind_017 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_018 | blind_test | yes | mask | 4 | 0ms | - | - |
| blind_020 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_022 | blind_test | yes | mask | 4 | 0ms | - | - |
| blind_023 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_029 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_030 | blind_test | yes | block | 2 | 0ms | - | - |
| blind_031 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_033 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_034 | blind_test | yes | block | 2 | 0ms | - | - |
| blind_036 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_037 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_038 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_039 | blind_test | yes | block | 3 | 0ms | - | - |
| blind_041 | blind_test | yes | block | 2 | 0ms | - | - |
| blind_042 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_043 | blind_test | yes | mask | 5 | 0ms | - | - |
| blind_044 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_055 | blind_test | yes | block | 2 | 0ms | - | - |
| blind_056 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_057 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_063 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_064 | blind_test | yes | block | 1 | 0ms | - | - |
| blind_065 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_067 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_068 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_069 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_070 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_074 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_075 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_076 | blind_test | no | mask | 2 | 0ms | secret_leakage | FN token:b1vf_F…(40) |
| blind_077 | blind_test | yes | block | 5 | 0ms | - | - |
| blind_082 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_083 | blind_test | yes | mask | 4 | 0ms | - | - |
| blind_085 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_086 | blind_test | yes | mask | 1 | 0ms | - | - |
| blind_088 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_090 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_091 | blind_test | yes | block | 4 | 0ms | - | FP password:change…(21) |
| blind_092 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_093 | blind_test | yes | mask | 3 | 0ms | - | - |
| blind_094 | blind_test | yes | block | 3 | 0ms | - | - |
| blind_095 | blind_test | yes | mask | 2 | 0ms | - | - |
| blind_096 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_097 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_098 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_103 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_104 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_106 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_107 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_111 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_116 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_118 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_119 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_122 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_127 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_128 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_129 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_131 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_136 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_137 | blind_test | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_139 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_141 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_142 | blind_test | no | mask | 1 | 0ms | detected, masked, overall_action | - |
| blind_144 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_148 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_150 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_155 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_156 | blind_test | yes | allow | 0 | 0ms | - | - |
| blind_158 | blind_test | yes | allow | 0 | 0ms | - | - |
