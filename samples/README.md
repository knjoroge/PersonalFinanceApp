# Sample CSVs

These files exist so you can try the importer end-to-end without exporting a real bank statement.

Upload any of them via **Transactions → 📁 Import / Export CSV → Upload a CSV file**.

| File | Format | Date style | Amount layout | What it tests |
|------|--------|------------|---------------|---------------|
| `chase_sample.csv` | Chase / BofA-style | US `MM/DD/YYYY` | Single `Amount` column (negative = expense) + `Type` | One-click auto-detect path with explicit Type column. |
| `natwest_sample.csv` | NatWest UK | UK `DD/MM/YYYY` | Split `Debit` / `Credit` columns | Two-column debit/credit fallback. |
| `wells_fargo_sample.csv` | Wells Fargo | US `MM/DD/YYYY` | Single Amount, **no header row** | Smart headerless detection. |
| `monzo_with_category_sample.csv` | Monzo UK | UK `DD/MM/YYYY` | Single Amount + **explicit Category column** | Auto-categorization (Food, Housing, etc. come from the bank — not all "Other"). |
| `unknown_bank_sample.csv` | Fictional bank | ISO `YYYY-MM-DD` | Unrecognised column names (`Trans Date`, `Withdrawal`, `Deposit`, `Memo`) | **Manual column-mapper UI** — auto-detect can't find date/amount, so the mapper appears. Try saving a preset called "MyBank" then re-import to see the preset dropdown. |
| `us_dates_sample.csv` | US generic | US `MM/DD/YYYY` (some ambiguous) | Single Amount | **Date-format toggle**. With the default DD-first setting, `10/05/2026` parses as 10 May. Re-import using the mapper UI with **MM-first** selected and it parses as 5 October. |

## Suggested test flow

1. Upload `chase_sample.csv` — should show ✅ "Format recognised automatically" with a 5-row preview, then one-click Import.
2. Upload `chase_sample.csv` again — every row should be reported as a duplicate (dedup safety).
3. Upload `unknown_bank_sample.csv` — should drop into the manual mapper. Map `Trans Date` → Date, `Withdrawal` → Debit, `Deposit` → Credit, `Memo` → Description. Save preset as "MyBank". Re-upload → the preset appears in the dropdown.
4. Upload `us_dates_sample.csv`. If your dates look wrong after import (e.g. day and month swapped), the mapper UI's date-format radio fixes it.
5. Upload `monzo_with_category_sample.csv` — note that transactions land in real categories (Food, Housing, Transportation, etc.) instead of all "Other".
