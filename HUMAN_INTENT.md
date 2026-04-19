# INTENT.md

User intents and desires for the helping-hands project.

## Active Intents

### App Deploys via GHA with Expected Behaviour (2026-04-19)

Pushing to `master` should deploy the app to lugiawyvern via GitHub Actions with
all features working — including multiplayer Hand World, Grill Me, and WebSocket
connectivity. Services must survive the GHA job lifecycle. See `WAITING_ON.md`
for the pending runner config change that makes this fully reliable.
