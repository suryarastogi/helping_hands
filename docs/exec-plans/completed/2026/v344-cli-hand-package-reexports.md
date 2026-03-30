# v344 — CLI Hand Package Re-exports

**Status:** completed
**Created:** 2026-03-30
**Completed:** 2026-03-30
**Theme:** Fix missing CLI hand re-exports at higher package layers

## Motivation

When `DevinCLIHand`, `DockerSandboxClaudeCodeHand`, `GooseCLIHand`, and
`OpenCodeCLIHand` were added to `cli/__init__.py`, the higher-level re-export
modules (`hands/v1/hand/__init__.py` and `hands/v1/__init__.py`) were not
updated to match. This meant anyone importing from the documented public
import surface at `helping_hands.lib.hands.v1` would get `ImportError` for
these newer hands.

## Tasks

- [x] Add `DevinCLIHand` to `hands/v1/hand/__init__.py` imports and `__all__`
- [x] Add `DevinCLIHand`, `DockerSandboxClaudeCodeHand`, `GooseCLIHand`,
      `OpenCodeCLIHand` to `hands/v1/__init__.py` imports and `__all__`
- [x] Add `DevinCLIHand` identity test to `test_hand_package_exports.py`
- [x] Add `DevinCLIHand` identity test to `test_cli_hand_package_exports.py`
- [x] Add all four missing hand identity tests to `test_hands_v1_package_exports.py`
- [x] Verify all tests pass (6604 passed, 76.04% coverage)

## Changes

| File | Change |
|---|---|
| `src/helping_hands/lib/hands/v1/__init__.py` | Added 4 CLI hand imports and `__all__` entries |
| `src/helping_hands/lib/hands/v1/hand/__init__.py` | Added `DevinCLIHand` import and `__all__` entry |
| `tests/test_hand_package_exports.py` | Added `DevinCLIHand` identity assertion |
| `tests/test_cli_hand_package_exports.py` | Added `DevinCLIHand` identity test |
| `tests/test_hands_v1_package_exports.py` | Added 4 missing hand identity tests |

## Tests

5 new test assertions across 3 test files. 6604 backend tests passed,
0 failures, 76.04% coverage.
