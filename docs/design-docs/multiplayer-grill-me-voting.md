# Design Doc: Multiplayer Grill Me — Plan Voting

## Context

Multiplayer Grill Me lets multiple tabs/participants collaborate on a single
Grill Me session. Solo Grill Me already has a three-phase UI (form → chat →
plan) culminating in a `## FINAL PLAN` that, when accepted, auto-populates and
submits the task form. The multiplayer variant needs a way for connected
participants to express agreement or dissent on the plan before it's submitted,
without over-engineering a voting system.

This doc records the decision for **Q6 — voting / consent model**. Prior Qs
(referenced below) established:

- **Q2** — membership is presence-based (connected tabs in the Yjs room).
- **Q4** — identity is hybrid; vote dedup is per-tab, not per-person.
- **Q5** — messages to the AI are batched/sent via explicit "Send to AI".

## Decision

**(i) Final-plan-only + advisory-with-block + revocable until submission.**

- Voting UI appears **only when `## FINAL PLAN` is emitted**. No per-turn
  voting, no per-participant "satisfied" signal.
- Each connected tab gets a single vote: 👍 or 👎. Votes are **revocable** —
  participants can change their vote any time before submission.
- The live tally is displayed next to Submit / Keep Grilling (e.g.
  "👍 3 · 👎 1").
- **Advisory-with-block:** the creator can always click Submit. If any
  participant has an active 👎 at submission time, Submit shows a confirmation
  dialog ("N participant(s) voted against this plan. Submit anyway?"). Creator
  can override.
- If the creator clicks **Keep Grilling**, the vote map resets — the next
  `## FINAL PLAN` is a fresh vote.
- **Override is recorded** on the submitted task: a line like
  `> Plan submitted over objection from N participant(s).` is prepended to the
  task prompt so downstream execution (and the git history) reflects the
  disagreement.

## Rationale

1. **Per-turn voting is scope creep.** It sounds appealing ("the AI reacts to
   our thumbs") but requires feeding vote counts into the AI's context,
   designing a prompt addendum, and reasoning about what the AI should *do*
   with a down-vote. Punt to v2.
2. **Per-participant "I'm satisfied" overlaps with Q5's batched-send model.**
   The "Send to AI" button already carries the "I have nothing more to add"
   signal implicitly. A parallel satisfaction button is redundant; a single
   Wrap Up press is simpler.
3. **Advisory-with-block threads the needle on thresholds.** Pure majority is
   brittle with presence-based membership (Q2) — disconnects shift the math
   under you. Hard thresholds ("≥2 up-votes") break the solo-in-multiplayer
   case. Unanimity gives any sulker a veto. Advisory-with-block respects that
   the creator is the accountable party (they own the submitting token) while
   still making dissent loud and visible. It also matches Q4's hybrid-identity
   decision: since vote dedup is per-tab, no numeric threshold should gate
   anything irreversible.
4. **Revocable until submission** is cheap (overwrite a Y.Map entry keyed by
   `player_id`) and matches how live collaborative UIs should feel. Bounded
   windows (e.g. 60s) create artificial urgency for an async-friendly feature.
5. **Final-plan-only keeps the UI minimal.** One voting widget, one moment of
   drama. Solo Grill Me already has the `plan` phase — multiplayer adds a
   tally plus a "Submit anyway" confirmation on top. Minimal diff.

## Implementation shape

- **Shared state:** a Yjs `Y.Map` named `votes` in the Grill Me room's Y.Doc.
  Keyed by `player_id`, values are `"up" | "down"`. The map is:
  - Created / revealed to the UI when the AI emits `## FINAL PLAN`.
  - Cleared (`map.clear()` in a transaction) when the creator clicks
    **Keep Grilling**.
- **Client UI:**
  - Vote buttons rendered next to Submit / Keep Grilling on the plan phase.
  - Live tally (`👍 N · 👎 M`) read from the Y.Map.
  - Each tab's own vote is highlighted; clicking the other option overwrites.
- **Submit flow (creator-only):**
  - `POST /grill/{id}/submit` — server-side auth: the caller's token hash
    must match `creator_token_hash` (Q4).
  - Server re-reads the Yjs vote map at submission time. If any `"down"`
    exists, return a soft-warning response. Client shows a confirmation
    dialog, then re-POSTs with `?override=true`.
  - On override, the server prepends
    `> Plan submitted over objection from N participant(s).` to the task
    prompt before handing off to the normal Helping Hands submission path.
- **Non-creator tabs** see the vote UI and live tally but don't see a Submit
  button (they see "Waiting for creator to submit…" or similar).

## Trade-offs

- **Per-tab dedup (Q4)** means one person with two tabs counts twice. We
  accept this because vote dedup by identity would require server-side
  token-hash lookup for every vote toggle and isn't worth the complexity
  for an advisory signal.
- **Creator bypass** means a determined creator can always submit over
  dissent. This is deliberate — the creator is the accountable party (owns
  the token) — but the override record preserves the dissent downstream.
- **No bounded window** means a stale vote from a disconnected tab can sit
  at 👎 indefinitely. Acceptable because (a) advisory, not blocking, and
  (b) presence cleanup (Yjs awareness timeout ~30s) will drop disconnected
  tabs; their votes can optionally be filtered by live-presence intersection
  at tally-render time.

## Open items deferred to implementation

- Whether the override-record line is a fixed template or configurable.
- Whether non-creator tabs see the Submit button greyed out or hidden
  entirely (cosmetic).
- Whether to filter the displayed tally by currently-present `player_id`s
  (avoids counting ghosts from dropped tabs).
