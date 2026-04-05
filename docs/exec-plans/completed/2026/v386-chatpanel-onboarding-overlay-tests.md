# v386 — ChatPanel & OnboardingOverlay Test Suites

**Status:** Completed
**Created:** 2026-04-05

## Goal

Add test suites for two previously-untested frontend components: `ChatPanel.tsx`
and `OnboardingOverlay.tsx`. These are the most self-contained untested UI
components remaining.

## Context

After v385 (DiffView, FileExplorer, useOnboarding tests), four components and
one hook remain untested: AsteroidsGame, ChatPanel, GrillMeOverlay,
OnboardingOverlay, and useGrillSession. ChatPanel and OnboardingOverlay are
pure presentational components with clear prop interfaces — ideal candidates
for unit testing.

## Tasks

- [x] Create `ChatPanel.test.tsx` covering:
  - Collapsed/expanded state rendering
  - Player name input and color picker
  - Presence panel (remote players)
  - Chat history (empty, messages, system messages)
  - Chat input (connected/disconnected, cooldown, typing indicator)
  - Emote picker toggle and emote selection
  - Form submission (send chat, trim whitespace, empty rejection)
- [x] Create `OnboardingOverlay.test.tsx` covering:
  - Step badge rendering (stepIndex / totalSteps)
  - Title and body display
  - Navigation buttons (Back/Next, first/last step)
  - "Got it!" label on final step
  - Dismiss button
  - Step dots (active, completed, pending)
  - Opacity 0 until positioned
- [x] Run frontend tests — all pass
- [x] Update INTENT.md, PLANS.md, Week-14 consolidation

## Acceptance criteria

- Both test files pass with `npm --prefix frontend run test`
- Meaningful coverage of component logic and rendering branches
- No changes to production code
