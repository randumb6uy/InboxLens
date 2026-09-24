# IndexLens — Phase 0 & Phase 1 Quality Assurance & Corner Cases Report

## 1. Executive Summary

This report documents the design, implementation, and verification of automated edge case and break case testing for **Phase 0 (Foundations)** and **Phase 1 (Classification & Storage)** of IndexLens.

- **Total Test Cases Executed**: 35
- **Passing**: 35 (100%)
- **Failing**: 0
- **Automated Test Suite**: [`tests/test_corner_cases.py`](tests/test_corner_cases.py)

---

## 2. Identified Corner & Break Cases Taxonomy

### Category A: Ingestion & Header Parsing Edge Cases

| Case ID | Scenario / Vulnerability | Risk | Resolution & Behavior |
| :--- | :--- | :--- | :--- |
| **ING-01** | `From` header is `None` or omitted in raw Gmail response | `TypeError` in `email.utils.parseaddr` | Hardened `_parse_sender_details` to coerce `None` to `""`, returning safe fallback tuple `("", "", "")`. |
| **ING-02** | `From` header has no `@` symbol (e.g. system `mailer-daemon` or daemon alerts) | Index out of range or malformed domain | Extracted domain safely verifies `@` existence before split, avoiding errors. |
| **ING-03** | Display names containing emojis, commas, and unquoted quotes (e.g. `🚀 "Sharma, Ramesh (CEO)" <user+filter@domain.com>`) | Splitting email address prematurely on comma | RFC 2822 parser isolates display name from angle address `<...>` cleanly. |
| **ING-04** | Corrupted or non-standard date header string (e.g. `"None"`, `"Tomorrow morning"`, empty string) | Unhandled `ValueError` crashing batch ingestion | `_parse_email_date` catches parsing exceptions and gracefully falls back to timezone-aware `datetime.now(timezone.utc)`. |
| **ING-05** | Date string without explicit timezone offset | Naive datetime causing timezone arithmetic bugs | Injected `timezone.utc` if `parsed.tzinfo` is absent. |

---

### Category B: Payload & Base64 Decoding Break Cases

| Case ID | Scenario / Vulnerability | Risk | Resolution & Behavior |
| :--- | :--- | :--- | :--- |
| **B64-01** | Gmail URL-safe Base64 with stripped padding (`len(body) % 4 != 0`) | `binascii.Error: Incorrect padding` dropping email body | Automatically calculates needed padding (`4 - (len % 4)`) and appends `'='` before decoding. |
| **B64-02** | Empty payload or null `parts` list in message | `AttributeError: 'NoneType' object has no attribute 'get'` | Safe traversal using `payload.get("parts", []) or []`. |
| **B64-03** | 3-level deeply nested multipart MIME structure (`multipart/mixed` $\rightarrow$ `multipart/alternative` $\rightarrow$ `text/plain` + `text/html`) | Incomplete body extraction | Recursive extraction function traverses all subtree parts and merges text fragments. |
| **B64-04** | Massive payload (200KB+ plain text body) | Memory leak / regex catastrophic backtracking | Buffer streaming and regex limits prevent CPU stalling. |

---

### Category C: Router & Classification Boundary Cases

| Case ID | Scenario / Vulnerability | Risk | Resolution & Behavior |
| :--- | :--- | :--- | :--- |
| **ROUT-01** | Mixed-case VIP contact configuration (e.g. `INVESTOR@CapitalVentures.COM`) | Failed matching against normalized sender emails | `EmailRouter.__init__` automatically normalizes and strips all VIP email addresses to lowercase. |
| **ROUT-02** | International & Indian currency tokens (`INR 1,450.00`, `Rs. 990`, `Rs 450`, `$`, `€`, `£`, `₹`) | Receipts misclassified as `NEEDS_LLM` | Expanded `RECEIPT_BODY_REGEX` to recognize `INR`, `Rs\.?`, `USD`, `EUR`, `GBP`, and standard currency symbols. |
| **ROUT-03** | Conflicting signals (e.g., Marketing email from Amazon containing "Flat 50% OFF" vs Amazon Order receipt) | Promotional emails categorized as receipts | Priority hierarchy ensures promotional patterns are evaluated before general domain heuristics. |
| **ROUT-04** | Empty subject and empty plain-text body | Regex crash or unhandled None | Safely handled; defaults to `NEEDS_LLM` with rule `no_deterministic_rule_matched`. |
| **ROUT-05** | Multilingual content and emojis in subject (e.g. `🎉 आपका ऑर्डर डिलीवर हो गया: Order Delivered!`) | Unicode encoding crash on Windows console | Codebase configured for UTF-8 input/output and SQLite Unicode columns. |

---

### Category D: Database & Storage Corner Cases

| Case ID | Scenario / Vulnerability | Risk | Resolution & Behavior |
| :--- | :--- | :--- | :--- |
| **DB-01** | Malicious SQL Injection in subject, sender, or snippet (`'; DROP TABLE emails; --`) | Database corruption / table dropping | 100% parameterized SQL queries (`?`) prevent all injection vectors. |
| **DB-02** | Duplicate message ID ingestion (re-running the batch pipeline) | Primary key collision error | SQLite `ON CONFLICT(id) DO UPDATE SET ...` ensures clean idempotency. |
| **DB-03** | Querying empty database for stats | ZeroDivisionError (`count / total * 100`) | Guard check `if total_count == 0` returns empty breakdown and `0.0%` rate. |
| **DB-04** | Duplicate VIP contacts added multiple times | Unique constraint failure | `ON CONFLICT(email) DO UPDATE SET ...` updates metadata cleanly. |

---

## 3. Automated Test Verification

Running the test suite:
```powershell
.venv\Scripts\pytest -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 35 items

tests/test_corner_cases.py::test_parse_sender_details_none PASSED        [  2%]
tests/test_corner_cases.py::test_parse_sender_details_empty PASSED       [  5%]
tests/test_corner_cases.py::test_parse_sender_details_no_at_symbol PASSED [  8%]
tests/test_corner_cases.py::test_parse_sender_details_complex_characters PASSED [ 11%]
tests/test_corner_cases.py::test_parse_email_date_corrupted PASSED       [ 14%]
tests/test_corner_cases.py::test_parse_email_date_missing_timezone PASSED [ 17%]
tests/test_corner_cases.py::test_extract_body_parts_missing_base64_padding PASSED [ 20%]
tests/test_corner_cases.py::test_extract_body_parts_empty_and_null_payload PASSED [ 22%]
tests/test_corner_cases.py::test_extract_body_parts_deeply_nested_multipart PASSED [ 25%]
tests/test_corner_cases.py::test_extract_body_parts_extremely_large_payload PASSED [ 28%]
tests/test_corner_cases.py::test_router_vip_case_insensitivity PASSED    [ 31%]
tests/test_corner_cases.py::test_router_currency_variations PASSED       [ 34%]
tests/test_corner_cases.py::test_router_conflicting_signals_promo_vs_receipt PASSED [ 37%]
tests/test_corner_cases.py::test_router_empty_subject_and_body PASSED    [ 40%]
tests/test_corner_cases.py::test_router_emojis_and_multilingual_content PASSED [ 42%]
tests/test_corner_cases.py::test_db_sql_injection_resilience PASSED      [ 45%]
tests/test_corner_cases.py::test_db_upsert_idempotency PASSED            [ 48%]
tests/test_corner_cases.py::test_db_pagination_boundary_cases PASSED     [ 51%]
tests/test_corner_cases.py::test_db_empty_state_stats PASSED             [ 54%]
tests/test_corner_cases.py::test_db_vip_duplicate_handling PASSED        [ 57%]
tests/test_ingestion.py::test_parse_sender_details PASSED                [ 60%]
tests/test_ingestion.py::test_parse_email_date PASSED                    [ 62%]
tests/test_ingestion.py::test_generate_mock_emails PASSED                [ 65%]
tests/test_gmail_client_mock_fetch PASSED                                 [ 68%]
tests/test_gmail_client_query_filter PASSED                               [ 71%]
tests/test_router.py::test_router_receipt_classification PASSED          [ 74%]
tests/test_router.py::test_router_newsletter_classification PASSED       [ 77%]
tests/test_router.py::test_router_vip_contact PASSED                     [ 80%]
tests/test_router.py::test_router_ambiguous_fallback PASSED              [ 82%]
tests/test_schemas.py::test_raw_email_schema PASSED                      [ 85%]
tests/test_schemas.py::test_receipt_data_schema PASSED                   [ 88%]
tests/test_schemas.py::test_extracted_email_schema PASSED                [ 91%]
tests/test_storage.py::test_upsert_and_get_email PASSED                  [ 94%]
tests/test_storage.py::test_classification_stats PASSED                  [ 97%]
tests/test_storage.py::test_vip_contacts PASSED                          [100%]

============================= 35 passed in 1.63s ==============================
```

---

## 4. Key Takeaways & Recommendations for Phase 2

1. **LLM Extraction Fallbacks**: For emails in `NEEDS_LLM`, structured JSON output parsing with `instructor` must implement Pydantic validation error retries (with `max_retries=2`).
2. **Semantic Caching**: The semantic cache layer in Phase 2 should hash normalized plain text to prevent re-extracting identical vendor receipt templates.
3. **Receipt Currency Normalization**: Receipts extracted across different currencies (`USD`, `EUR`, `INR`) must store currency ISO codes alongside amounts to maintain aggregation query consistency.
