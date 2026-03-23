# v288 — useSchedules Branch Coverage

**Goal:** Raise `useSchedules.ts` branch coverage from 60% to >80%.

**Result:** 100% statements, 94.59% branches. Overall frontend: 89.57% / 82.67%.

## Tests added (9 new, 22 total)

1. `triggerSchedule` — confirm cancelled → no fetch
2. `triggerSchedule` — API error → sets scheduleError
3. `toggleSchedule` — API error → sets scheduleError
4. `toggleSchedule` — enable path (previously only tested disable)
5. `openEditScheduleForm` — API error → sets scheduleError, editingScheduleId stays null
6. `deleteSchedule` — API error → sets scheduleError
7. `saveSchedule` — edit mode uses PUT to `/schedules/:id`
8. `saveSchedule` — API error → sets scheduleError
9. `saveSchedule` — optional fields (model, pr_number, github_token, reference_repos, tools, skills) included in body

## Files changed

| File | Change |
|---|---|
| `frontend/src/hooks/useSchedules.test.tsx` | +9 tests covering error paths, edit mode, optional fields |
| `INTENT.md` | Added v288 completion entry |
