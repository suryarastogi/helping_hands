# Design Doc: Multiplayer Grill — Plan Voting

## Status

Accepted (design-only). Multiplayer grilling is not yet implemented; this
doc records the voting-mechanic decision ahead of the feature build so the
implementation plan does not have to re-litigate it.

## Context

Grill Me (`src/helping_hands/server/grill.py`) currently runs as a solo
interactive planning session: one user chats with an AI "interviewer" that
stress-tests the design until a `## FINAL PLAN` block is emitted, which the
frontend then pipes into the submission form.

A future extension layers **multiplayer** on top — several participants
(creator + spectators who walked into the same Hand World session) can watch
the chat and weigh in before the plan is submitted as a build task. The Yjs
awareness/Y.Doc infrastructure used for Hand World
(see [multiplayer-hand-world.md](multiplayer-hand-world.md)) is the
natural transport.

The open question: when the AI produces `## FINAL PLAN`, how binding are
non-creator participants' votes on whether to submit it?

## Options considered

- **A — Advisory only.** Show vote tally; creator decides and submits.
- **B — Soft gate.** Creator submits, but a confirmation modal appears if
  any participant down-voted.
- **C — Majority gate.** Submit is disabled unless a majority of
  participants up-vote.
- **D — Unanimous gate.** Any down-vote blocks submission.

## Decision

**Option A (advisory only), with per-user vote visibility as a refinement.**

1. The creator owns the repo and the GitHub token. They are the party
   accountable for the build outcome and should retain the final call. A
   hard gate means Hand World walk-ins can deadlock someone else's
   workflow by down-voting and leaving — a griefing vector that adds zero
   real safety, because the authorization boundary is the token, not the
   vote.
2. A soft gate (B) buys very little. The creator already sees the tally;
   a confirmation modal on top is noise. The real signal is *who* voted
   how, not a generic "are you sure?".
3. Hard gates (C/D) invite coordination problems. Users disconnect, Yjs
   awareness flickers during reconnect, and down-voters can be "phantoms"
   whose votes cannot be retracted because they are gone. Pinning down
   "active participant" tightly enough to make D reliable is surprisingly
   hard.
4. The value of multiplayer grilling is the *grilling*, not the vote.
   Objections surface during the chat; by the time the final plan is
   emitted, the creator has already heard them. The vote is a lightweight
   "did we land it?" ritual, not a gate.

### Refinement

- Tally is visually prominent in the overlay.
- Per-user vote badges appear next to each roster entry so the creator
  can see exactly who dissented.
- If anyone down-votes, inline-display the dissenter's name near the
  Submit button as a gentle nudge (e.g. "Alice voted against this
  plan") — but do not disable submission.

## Sub-decisions

- **Voting window:** votes are only accepted after `## FINAL PLAN`
  appears. Voting on a half-formed conversation is meaningless.
- **Vote change:** allowed. Model votes as
  `Y.Map<player_id, "up" | "down">` with last-write-wins — trivial in
  Yjs and matches user expectations.
- **Voter eligibility:** anyone currently in the session's Yjs awareness
  **or** anyone who has sent ≥1 chat message in the session. Prevents
  silent lurker inflation without requiring a separate "registered
  voters" concept.
- **"Keep Grilling" scope:** any participant (not just the creator) can
  click Keep Grilling. It sends a canned message and reopens the chat
  phase for everyone. This is the pressure-release valve when
  participants dissent — if the creator sees down-votes they disagree
  with, they submit anyway; if they agree, they (or any participant)
  click Keep Grilling to pull dissenters back into another round.

## Consequences

- No hard authorization boundary in the voting layer; abuse prevention
  relies on session presence plus the GitHub token boundary at submit
  time.
- Vote state lives in the Y.Doc (persistent) rather than awareness
  (ephemeral) so the tally survives a participant's brief reconnect.
- The frontend must render three things that were not part of solo grill:
  the per-user vote badges in the roster, a tally summary near the
  Submit button, and the dissenter nudge line.
- No new backend endpoint is strictly required for voting itself — Yjs
  sync handles it — but server-side validation of the vote map (enum
  check on values, cap on map size) should follow the
  `validate_awareness_state()` pattern in `multiplayer_yjs.py`.

## Alternatives not chosen

B/C/D are rejected for the reasons above. A middle-ground "creator-only
veto" (creator's vote is hard-binding, others are advisory) was also
considered but collapses to A in practice: the creator already controls
the Submit button.

## Future extensions

- If griefing or confusion around advisory votes becomes a real problem,
  revisit with data and consider B (soft gate) before C/D.
- Persist a compact record of the final vote tally alongside the task's
  metadata so post-hoc review can see who endorsed which builds.
