# SAP Credentials Implementation Summary

**Date:** 2026-08-07
**Scope:** Web UI SAP credential input (username + password from form; mandant/language/system from `.env`)

## Files Modified

### 1. `web/.env.example`
Added SAP connection variables as fixed configuration (not user-editable in the form):

```ini
SAP_SYSTEM="ERQ"
SAP_MANDANT="200"
SAP_LANG="ES"
```

### 2. `web/templates/index.html`
- **New CSS class `.credentials-row`** — styled row for credential inputs, matching existing design language (14px font, blue focus ring, 200px-wide inputs).
- **New HTML block** between the status badge and the file input row: two labeled inputs (`#sap-user` text, `#sap-pass` password) with `autocomplete="off"`.
- **Updated JS `btnRun` click handler**:
  - Reads `sap-user` and `sap-pass` values before dispatching.
  - Client-side validation: rejects empty username or password with log messages.
  - Changed `fetch('/execute')` to send `POST` with `Content-Type: application/json` and body `{ username, password }`.

### 3. `web/server.py`
- **`_run_sap_process(file_path, username, password)`** — signature expanded to accept credentials.
- **Sap module globals override** (lines 204-213): After `from sap import SapGui`, imports `sap as sap_module` and sets:
  - `sap_module.mandt` ← `os.environ["SAP_MANDANT"]`
  - `sap_module.username` ← form-provided `username`
  - `sap_module.password` ← form-provided `password`
  - `sap_module.language` ← `os.environ["SAP_LANG"]`
  - `sap_module.system_sap` ← `os.environ["SAP_SYSTEM"]`
- **`execute()` endpoint**: Reads JSON body via `request.get_json()`, validates that both `username` and `password` are non-empty (returns 400 otherwise), passes them to the background task.

## Files NOT Modified
- `script/sap.py` — untouched (read-only contract honored).
- `script/*` — no changes whatsoever.

## Data Flow

```
Browser form (user types username + password)
  → JS validates non-empty
  → POST /execute { username, password }
  → server.py execute() validates, reads SAP_MANDANT/LANG/SYSTEM from env
  → _run_sap_process() sets sap module globals
  → SapGui().sapLogin() reads those globals and connects to SAP
```

## Verification Checklist
- [x] HTML form has `#sap-user` (text) and `#sap-pass` (password) fields
- [x] JS client-side validates both fields non-empty before calling `/execute`
- [x] `fetch('/execute')` sends JSON body `{ username, password }` with correct Content-Type
- [x] `server.py` reads `username`/`password` from `request.get_json()` and validates
- [x] `_run_sap_process` sets all 5 sap module globals before `sapLogin()` call
- [x] Mandant, language, system come from `.env` via `os.environ.get()`
- [x] `script/` directory untouched
