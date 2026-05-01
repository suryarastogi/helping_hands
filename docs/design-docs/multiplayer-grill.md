# Design Doc: Multiplayer Grill Me

## Context

"Grill Me" (solo) is an AI interview session where one user stress-tests a
plan with the AI before submitting it as a Helping Hands task. Multiplayer
Grill Me extends the same idea to several users collaborating on a single
interview session — surfaced via a campfire sprite in Hand World
(proximity-activated, mirroring the arcade pattern).

Solo Grill Me is left untouched; this is a parallel feature with its own
Celery task, REST prefix (`/mgrill`), and Yjs rooms.

## Decision

Build a **registry** of concurrent sessions (not a singleton), keyed by the
Celery task ID and discoverable through a lobby. Every session is backed
by:

- **A Yjs room** `mgrill-{session_id}` that owns the transcript, vote
  tally, and pending batch.
- **Redis keys** for authoritative server state (status, creator identity,
  turn count) and the worker's user-message FIFO.
- **A Celery task** `mgrill_session` that runs the AI interview loop,
  reusing solo Grill Me's Claude/Codex CLI invocation helpers verbatim.

The transport split mirrors the distinction between "broadcast fabric"
(Yjs, sub-100ms) and "state store" (Redis, authoritative for auth
decisions).

## Approach

### Transport — pure Yjs for live data, Redis for authority

| Data                           | Storage                               | Who reads               | Who writes                          |
|--------------------------------|---------------------------------------|-------------------------|-------------------------------------|
| Transcript (messages)          | Y.Array `messages` in Yjs room        | Frontend subscribes     | Endpoints (user turns); bridge task (AI turns) |
| Votes                          | Y.Map `votes` in Yjs room             | Frontend + `/submit`    | `/vote` endpoint                    |
| Pending batch                  | Y.Map `pending` in Yjs room           | Frontend + `/send`      | `/pending`, `/send` endpoints       |
| Session status / creator       | Redis `mgrill:{id}:state`             | Endpoints + worker      | Endpoints + worker                  |
| User→worker queue              | Redis `mgrill:{id}:user_msgs`         | Worker                  | `/send` endpoint                    |
| AI→bridge envelope queue       | Redis `mgrill:ai_outbox` (shared)     | Bridge task             | Worker                              |
| Session registry               | Redis sorted set `mgrill:sessions`    | `/mgrill/sessions` GET  | All activity-bumping endpoints      |

### Yjs room naming — full mount-prefixed path

The pycrdt `WebsocketServer` keys rooms by the full `scope["path"]` of the
incoming WebSocket, not the post-mount path. Starlette's
`app.mount("/ws/yjs", _yjs_app)` updates `scope["root_path"]` but leaves
`scope["path"]` unchanged — so a client connecting to
`ws://host/ws/yjs/hand-world` creates a room keyed
`"/ws/yjs/hand-world"` on the server, and any in-process call from our
endpoints or bridge must use the same full-prefix key or it ends up
with a *second* Y.Doc that nobody else observes.

The `mgrill_room_name(session_id)` helper returns
`/ws/yjs/mgrill-{session_id}` and must be used for every server-side
`get_room()` call — never construct the key by hand. An earlier version
of this module used the bare `mgrill-{sid}` and every AI turn landed
silently in an orphan Y.Doc; the only diagnostic was "`turn_count`
advances but the transcript stays empty." Fixed via end-to-end probe.

### The worker→Yjs bridge

The Celery worker runs in a separate process from the FastAPI server (and
the Yjs WebSocket server). `pycrdt` 0.12 does not ship a Python Yjs
client, so the worker cannot speak Yjs directly to the WS server. Rather
than hand-roll the sync protocol, an **in-process asyncio task**
(`mgrill_bridge`) drains a shared Redis list (`mgrill:ai_outbox`) and
appends each envelope to the target room's `messages` Y.Array
*in-process*. The Yjs server's normal broadcast observers then push the
update to every connected client with CRDT-normal latency.

```
worker.run()
  └── _emit_message(r, sid, ...)
        └── LPUSH mgrill:ai_outbox {session_id, role, content, ...}

                                                         [FastAPI process]
                                                            │
                                                 mgrill_bridge loop
                                                            │
                                                     LPOP mgrill:ai_outbox
                                                            │
                                       get_room("mgrill-{sid}").ydoc["messages"].append(...)
                                                            │
                                                  Yjs server broadcast
                                                            │
                                               y-websocket in browser
```

### Single-drainer guarantee — Redis leader lock

The bridge writes to an **in-memory** Y.Doc owned by the FastAPI process it
runs in. That's the whole latency story — no extra network hop — but it
also means a Y.Doc mutation is only visible to clients connected to the
same process. If two or more FastAPI processes each run their own bridge
task (e.g. `uvicorn --workers N > 1`, `--reload` which forks a worker
alongside the reloader, or leftover zombies from a sloppy restart), they
race `LPOP` on the shared outbox:

- Whichever bridge wins the race writes to *its* Y.Doc.
- The browser's WebSocket lands on only one of the processes.
- Any envelope drained by a non-browser-bound process is lost — the
  transcript stays empty while `turn_count` in Redis advances.

We hit exactly this in prod: four zombie uvicorns from failed restart
cycles stole ~75% of AI turns into orphaned Y.Docs.

**Fix: a Redis leader lock** (`mgrill:bridge:leader`) ensures exactly one
bridge drains at a time:

- **Acquire**: `SET mgrill:bridge:leader <unique_token> NX EX 5` — atomic
  "only one winner". Failed acquirers sleep 1 s and retry (standby mode,
  zero outbox reads).
- **Renew**: a Lua `GET+PEXPIRE` every 2 s while draining. Runs atomically
  against the compared token so the leader can't accidentally renew a
  token it no longer owns.
- **Release**: a Lua `GET+DEL` on shutdown, same compare-and-delete
  pattern to avoid deleting a peer's lock after an expiry-driven takeover.
- **Failover**: 5 s TTL means a crashed leader's lock lapses and a peer
  takes over within 5 s. Clean shutdown releases immediately.

Token format is `{pid}-{uuid12}` — reclaimable across restarts, unforgeable
by a peer on the same host.

```
[process A]                           [process B]                    Redis
     │                                     │                           │
SET leader A NX EX 5 ─ ── ── ── ── ── ── ──┼ ── ── ── ── ── ── ── ─→  (key: A, ttl 5s)
     ← True                                │
     ├─ drain LPOP mgrill:ai_outbox        │
     ├─ renew every 2s (Lua GET+PEXPIRE)   │
     │                                     SET leader B NX EX 5 ── ── ─→ (conflict)
     │                                     ← False — sleep 1s, retry
     │                                     │
… process A crashes …                      │
                                           SET leader B NX EX 5 ── ── ─→ (after ≤5s)
                                           ← True
                                           └─ drain LPOP mgrill:ai_outbox
```

Standby processes do **zero** `LPOP` calls, so outbox entries are safe even
during failover-window overlaps.

Alternatives considered:

- **Worker-as-Yjs-client** (option 1). Cleaner in principle, but `pycrdt`
  dropped its WebsocketProvider; we'd need to hand-roll the sync protocol
  or add a second CRDT library. Rejected as net-negative complexity.
- **Keep messages in Redis** (pre-migration). Works, matches solo Grill
  Me, but loses the sub-100ms latency and per-entry CRDT merge behaviour
  that makes concurrent editing feel live. Rejected as a deviation from
  the locked plan.

### Turn-taking — collaborative batched

Participants type into a shared **pending batch** (anyone with a valid
token can add); any token-holder presses Send to AI. The `/send` endpoint
reads the Y.Map `pending`, appends one transcript entry per author to
`messages`, clears the Y.Map, and bundles the entries as a single user
message prefixed `[Name]: ...` joined by blank lines. The worker pops
that bundled text from `mgrill:{id}:user_msgs` and runs one AI turn.

The system prompt adds: "Multiple participants may collaboratively answer.
Each turn you receive may contain messages from multiple users, formatted
as `[Name]: <message>`. Address participants by name when their answers
conflict."

### Voting and submission

Voting UI appears **only** when the AI emits `## FINAL PLAN`. Each
participant (per `player_id`) can up/down-vote; the tally lives in the
room's `votes` Y.Map. The creator is the sole decider of submit; dissent
is advisory but surfaced:

- `POST /mgrill/{id}/submit` reads the tally at submit time.
- If any `down` vote is present, returns **409 Conflict** with
  `{"down_votes": N, "up_votes": M, "total_votes": T}`.
- The creator can retry with `?override=true`. The override is recorded
  server-side in `mgrill:{id}:state.submit_override_count` (never
  prepended to the submitted task prompt).

### Creator handoff

Each session has exactly one creator (tracked by `creator_token_hash` in
Redis). Creators heartbeat via `POST /mgrill/{id}/heartbeat` every 20s.
If `now - creator_last_seen_ts > 60s`, any valid token-holder can
`POST /mgrill/{id}/claim-creator` and take over. A system hint is posted
into the transcript Y.Array.

### Per-tab vote dedup

Votes are keyed by `player_id`, a per-tab UUID stored in `sessionStorage`
(`hh_mgrill_player_id_v1`). This means a single person with three tabs
can cast three votes. The UI surfaces this explicitly ("Votes are per
tab, not per person — consensus signal only"). Acceptable because voting
is advisory; the creator is the accountable submitter.

## Identity / auth matrix

Mirrors the schedules ownership pattern. When the server has a global
`GITHUB_TOKEN` configured, identity is server-owned and the per-user
token requirements are lifted — any caller is treated as creator.

| Server `GITHUB_TOKEN` | Client `X-GitHub-Token` | Can chat / vote / add to batch | Can Submit / Keep Grilling / Heartbeat |
|-----------------------|--------------------------|--------------------------------|-----------------------------------------|
| unset                 | unset                    | no — 401                       | no — 401                                |
| unset                 | set                      | yes                            | only the session creator (and `ADMIN_GITHUB_TOKEN`) |
| **set**               | **unset**                | **yes** (server token used)    | **yes — anyone**                        |
| set                   | set                      | yes                            | yes — anyone                            |

Implementation:

- `_mgrill_effective_token(request)` falls back to `os.environ["GITHUB_TOKEN"]`
  when the client has not sent `X-GitHub-Token`.
- `_mgrill_require_token(request)` raises 401 only when *neither* token
  is available.
- `_mgrill_require_creator(state, token_hash)` short-circuits with "pass"
  when `_server_has_github_token()` is true — so Submit / Keep Grilling /
  Heartbeat / non-author delete-pending endpoints unlock for all callers.
- `GET /mgrill/{id}` reports `is_creator=true` for every caller when the
  server has a token, so the frontend exposes creator actions to everyone.

Frontend companion (`MultiplayerGrillRoom`):

```ts
// Server-wide token unlocks token-gated UI for everyone.
const hasToken = serverHasGithubToken || Boolean(loadGithubToken());
```

The read-only banner, the "add a GitHub token" hint in the lobby, and the
claim-creator button all auto-hide when `hasToken` is true or when the
server owns identity.

`ADMIN_GITHUB_TOKEN` continues to satisfy the creator check per-user —
the usual escape hatch when the server has no global token.

## Trade-offs

- **In-memory Yjs state** — a server restart drops transcripts for active
  sessions. The Celery task survives (Redis-backed state), so the
  interview can resume, but history before the restart is gone. A
  `YStore` (pycrdt's persistence hook) would fix this at the cost of a
  new dependency surface.
- **100ms bridge poll** — trades idle CPU for responsiveness.
  Sub-second end-to-end latency for AI messages is achievable, but the
  leader burns a `LPOP` per 100 ms (standby peers don't poll). Could
  switch to `BLPOP` with a blocking timeout if the idle cost ever becomes
  visible.
- **Leader-lock TTL = 5 s** — after a leader crash, AI turns stall for up
  to 5 s before a peer takes over. Tuned short enough to feel snappy,
  long enough that brief event-loop pauses (e.g. GC) can't accidentally
  drop leadership. The 2 s renewal cadence gives three renewal attempts
  per TTL window — any one succeeding keeps leadership.
- **Per-tab vote dedup** — deliberately weak (see above). Stronger dedup
  would require token-based voting, which excludes read-only viewers who
  don't have a GitHub token stored.
- **Server-token mode grants everyone creator power** — by design.
  Teams running a shared server instance can collaborate without
  provisioning per-user tokens; the operational control boundary is the
  server's `GITHUB_TOKEN`, not per-session ACLs. Use per-user mode when
  the caller-pool is mixed-trust.
- **Creator heartbeat is 20s / handoff is 60s** — tuned so a closed tab
  transfers control without stranding the session, but a brief network
  blip doesn't trigger a surprise handoff. In server-token mode this is
  moot (handoff UI is suppressed).

## Key files

| Layer     | File                                                         |
|-----------|--------------------------------------------------------------|
| Worker    | `src/helping_hands/server/multiplayer_grill.py`              |
| Bridge    | `src/helping_hands/server/mgrill_bridge.py`                  |
| REST      | `src/helping_hands/server/app.py` (`/mgrill/*` endpoints)    |
| Hook      | `frontend/src/hooks/useMultiplayerGrill.ts`                  |
| Overlay   | `frontend/src/components/MultiplayerGrillOverlay.tsx`        |
| Lobby     | `frontend/src/components/MultiplayerGrillLobby.tsx`          |
| Room      | `frontend/src/components/MultiplayerGrillRoom.tsx`           |
| Sprite    | `frontend/src/components/HandWorldScene.tsx` (`hh-mgrill-campfire`) |
| Tests     | `tests/test_multiplayer_grill.py`, `tests/test_mgrill_bridge.py` |

## Endpoints

| Method | Path                                           | Auth                                 | Effect                                          |
|--------|------------------------------------------------|--------------------------------------|-------------------------------------------------|
| POST   | `/mgrill/sessions`                             | Effective token required             | Enqueue `mgrill_session` Celery task            |
| GET    | `/mgrill/sessions`                             | Public (session registry is global)  | Lobby listing, sorted by last activity          |
| GET    | `/mgrill/{id}`                                 | Public (token affects `is_creator`)  | Redis state snapshot + Yjs participant count    |
| POST   | `/mgrill/{id}/pending`                         | Effective token required             | Append to Y.Map `pending`                       |
| DELETE | `/mgrill/{id}/pending/{pending_id}`            | Effective token + author or creator  | Delete from Y.Map `pending`                     |
| POST   | `/mgrill/{id}/send`                            | Effective token required             | Bundle + clear pending, push to `user_msgs`     |
| POST   | `/mgrill/{id}/vote`                            | Public (player_id-keyed, no auth)    | Upsert Y.Map `votes`                            |
| POST   | `/mgrill/{id}/submit` (`?override=`)           | Effective token + creator bypass     | Enqueue `build_feature`; 409 on dissent w/o override |
| POST   | `/mgrill/{id}/keep-grilling`                   | Effective token + creator bypass     | Clear votes, hint → transcript, status→active   |
| POST   | `/mgrill/{id}/claim-creator`                   | Effective token required             | Take over after 60s creator absence             |
| POST   | `/mgrill/{id}/heartbeat`                       | Effective token + creator bypass     | Refresh `creator_last_seen_ts`                  |

"Creator bypass" = the check is skipped entirely when
`_server_has_github_token()` (see auth matrix above).

## Feature flag

All endpoints are gated by `GRILL_ME_ENABLED=1` — same flag as solo Grill
Me. The world sprite is only rendered when the server-config endpoint
reports `grill_enabled: true`.
