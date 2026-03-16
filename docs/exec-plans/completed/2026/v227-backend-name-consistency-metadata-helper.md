# v227 — Fix backend name inconsistency, DRY metadata builder, DRY message dict

**Status:** Completed
**Created:** 2026-03-16
**Branch:** helping-hands/claudecodecli-153b72b7

## Problem

1. **Backend name bug** — `langgraph.py` and `atomic.py` use hardcoded
   `backend="langgraph"` and `backend="atomic"` in both `_finalize_repo_pr()`
   calls and response metadata, instead of `self._BACKEND_NAME` which resolves
   to `"basic-langgraph"` and `"basic-atomic"`. This means PR descriptions and
   response metadata report incorrect backend names for these hands.

2. **Repeated metadata dict** — The pattern
   `{"backend": ..., "model": self._hand_model.model, "provider": self._hand_model.provider.name, **pr_metadata}`
   is duplicated in 5 locations (langgraph run/stream, atomic run/stream,
   iterative run×2, cli/base). A `_build_response_metadata()` base class helper
   would DRY this.

3. **Repeated LangChain message dict** — The pattern
   `{"messages": [{"role": "user", "content": prompt}]}` appears 4 times in
   langgraph.py (2) and iterative.py (2). A helper or constant can centralize
   this.

## Tasks

- [x] Fix `langgraph.py` to use `self._BACKEND_NAME` instead of `"langgraph"` (3 sites)
- [x] Fix `atomic.py` to use `self._BACKEND_NAME` instead of `"atomic"` (3 sites)
- [x] Add `_BACKEND_NAME` class constant to `LangGraphHand` and `AtomicHand`
- [x] Extract `_build_response_metadata()` helper on `Hand` base class
- [x] Replace metadata dict construction in all 5 locations
- [x] Extract `_langchain_user_message()` static helper on iterative base
- [x] Replace message dict construction in 4 locations
- [x] Add tests for backend name consistency
- [x] Add tests for `_build_response_metadata()`
- [x] Add tests for `_langchain_user_message()`
- [x] Run full test suite, lint, type check

## Completion criteria

- All hardcoded backend strings replaced with `_BACKEND_NAME`
- Metadata dict built via shared helper in all hands
- Message dict built via shared helper in LangGraph hands
- Tests pass, lint clean, types clean
