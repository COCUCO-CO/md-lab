# G4 Multi-campaign — Step 02: Repo-wide ruff cleanup (zero-error goal)

**Step**: 02 — Bring the whole GUI tree (`gui/backend`, `gui/tests`, `gui/__init__.py`) to 0 ruff errors, per the user's request "dejar todo arreglado ... sin errores" (fix everything, no errors), excluding items that require a human decision.

**Status**: completed

## Scope decision

- In scope: every Python file under `5ht2a_md/gui/` (`backend/`, `tests/`, `__init__.py`) — the G-series GUI project (ruff target `py310`, `line-length 88`, select `E,F,I,UP,B,BLE,RUF,EXE`).
- Out of scope (separate project, not touched): the `htr2a_md` CLI package and `scripts/` at the `5ht2a_md/` level. They have their own `pyproject.toml` (ruff target `py312`) and require Python ≥3.12, while the runtime here is 3.10.9; they are the scientific MD pipeline, not the GUI.
- No scientific/safety behaviour changed: no thresholds, gates, force-field parameters, protonation logic, driver commands, or `pilot` exposure were altered. The only string-content change is the campaign "DRUG_ACTIVE" message made dynamic (see below), which also satisfies the `risperidone` grep gate.

## Implemented changes

- **`ruff --fix` (safe, auto-applicable rules)**: applied across `backend/` + `tests/` (imports sorting I001, unused imports F401, `UP` modernisations, etc.). Reverted the `UP017` `datetime.UTC` auto-fix in 8 files back to `timezone.utc` because the runtime is Python 3.10.9 (`datetime.UTC` is 3.11+).
- **F821 (undefined names)**: added missing `Any` imports (`backend/events.py`, `tests/unit/test_manual_verify.py`), `import pytest` (`tests/unit/test_step_card_contract.py`), `import os` (`tests/contract/test_driver_system_flag.py`, after replacing the long `__import__("os")` idiom with a plain `os.environ`).
- **F811 (redefinition)**: removed the shadowed `attempt_complete` import in `routes/manual.py`.
- **B904 (raise ... from)**: added `from exc` / `from e` / `from None` to 13 intentional exception re-raises.
- **F841 (unused local)**: removed 14 unused locals after verifying each had no side effect.
- **B007, E402, E741** (`l` → `seg_l` in `runs.py`), **RUF001/002/003/005/013/015**, **UP031/038**: fixed.
- **BLE001 (blind except)**: added `# noqa: BLE001` to 21 intentional defensive `except Exception` blocks (deliberate fail-safe catches, not swallowed errors).
- **E501 (line too long)**: the bulk of the remaining debt. Fixed `backend/` file-by-file (ternaries → if/else, multi-line dict/list/return wraps, docstring re-wraps, long string/path splits) and `tests/` file-by-file (assert-message paren wraps, `client.post/get` wraps, long path/URL/list splits, docstring re-wraps).
- **`backend/catalog.py`** (115 E501) and **`backend/glossary.py`** (rewritten as a list of `{"term","definition"}` dicts) brought to clean.
- **Dynamic campaign message** in `routes/campaign.py`: the hardcoded `"Risperidone is DRUG_ACTIVE; LSD cannot start..."` string now uses `info['active_ligand_id']` / `ligand_id`, removing the hardcoded ligand name (satisfies the `risperidone` grep gate). Verified no test asserts the exact old message.

## Errors found & fixes (introduced during cleanup, all caught and reverted)

- **UP017 broke the runtime**: `ruff --fix` rewrote `timezone.utc` → `datetime.UTC` (3.11+); reverted all 8 files to `timezone.utc` (3.10.9 runtime).
- **Lost-space string concatenation (content bug)**: the E501 wrap scripts split string literals and dropped the boundary space (e.g. `"Occupancy at"` + `"0.40 nm"` → `"at0.40"`), silently changing scientific text. Caught by `tests/unit/test_readings.py::test_no_invented_cutoffs` failing with `AssertionError: {'3', '40', '5'}`. Wrote a lost-space detector (line ends with a closing quote with no following comma/colon, next line starts with an opening quote, boundary chars alphanumeric) → found and fixed 46 occurrences in `backend/` (`glossary.py` 11, `manual.py` 1, `readings.py` 34); verified 0 in `tests/`. Detector now reports 0 in both trees.
- **`backend/main.py` corruption**: a wrap pattern split on ` and ` that sat *inside* the string literal `"GUI is running. See /api/system and /api/replicas."`, leaving the original line plus two broken fragments → 10 `SyntaxError`s. Deleted the orphaned fragments and wrapped the line as a multi-line dict. Made the wrap script's return-expression pattern paren-only (no splitting on ` and `/` or ` inside strings) and skip if still >88.
- **`tests/unit/test_manual_verify.py` corruption**: an earlier wrap run left orphaned continuation fragments (e.g. a dangling `"HTR2A_...", "f6_cgenff", record)` after a `_save_record(...)` block) → 10 `SyntaxError`s. Removed the orphaned fragments and re-applied the intended wraps.
- **`routes/evidence.py` F821 `Response`**: an annotation `-> Response` was added without importing `Response`; corrected to `-> dict` (the function returns a metadata dict).
- **`test_evidence_path.py` F541**: stray `f` prefixes on placeholder-free f-strings removed.
- **`test_driver_system_flag.py` F821 `os`**: the long-line fix used `os.environ` without importing `os`; added `import os`.

## Verification (final, run from `/home/tomas/PycharmProjects/md-lab` with `PYTHONPATH=$PWD/5ht2a_md`)

1. `python -m pytest 5ht2a_md/gui/tests/unit 5ht2a_md/gui/tests/contract 5ht2a_md/gui/tests/integration -q` → **288 passed**, exit 0.
2. `P11_REQUIRE_VISUAL=1 python -m pytest 5ht2a_md/gui/tests/visual -q` → **38 passed**, exit 0.
3. `ruff check backend/ tests/ __init__.py` (from `5ht2a_md/gui`) → **All checks passed!**, exit 0 (0 errors, down from 893 pre-existing at the start of this phase).
4. `! grep -rn "risperidone" backend/ --include=*.py` → no matches, exit 0.
5. `! grep -rn "SYSTEM_ID" backend/config.py` → no matches, exit 0.
6. `! grep -rn "discover_system_id" backend/ --include=*.py` → no matches, exit 0.
7. `from gui.backend.main import app` → imports cleanly, 60 routes registered.

## Open items (require a human decision — left intact, flagged)

- **P05 approval-verdict gap (safety semantics)**: `validate_approval_record()` checks only gate + sha256, but the P05 spec requires the cited JSON `overall_verdict == PLATEAU` for `F11_segment0` and `pilot_decision == PASS` + `len(replicas) >= 3` for `F14_extend_250`. Changing this alters safety behaviour → needs a human-approved decision record.
- **Campaign-state contradiction**: `config/campaign_order.yaml` = `COMMON_INFRASTRUCTURE_PENDING` vs `config/campaign_state.json` = `DRUG_ACTIVE`/risperidone — which file is authoritative is a user decision. (`routes/campaign.py::_read_order()` reads `state`/`campaign_state` keys but the real file uses `status`.)
- **GPU lease route-level acquire/release**: running jobs left unprotected; explicitly G4.2 collision-safety scope (user previously forbade starting G4.2).
- **Stale `md-lab/gui` namespace dir** at the repo root (no `__init__.py`): can shadow the real `gui` package if `PYTHONPATH` is unset. Not deleted (footgun, needs a decision).

## Overall state

The entire GUI tree is now 0 ruff errors and 326/326 tests passing (288 non-visual + 38 visual). The three G4.1 grep gates still pass. No scientific/safety behaviour was changed; the four items above are the only remaining open points and each requires a human decision.
