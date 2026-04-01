# Repo Selection UI: Chips, Suggestions & Recent Repos

## Context

Users interact with two repo-related fields in the frontend:

1. **repo_path** — the target repository (`owner/repo` format), a single value
2. **reference_repos** — zero or more read-only context repos the AI agent can browse

Both fields benefit from remembering previously used repos so users don't have to retype them. The reference repos field additionally needs multi-value support since users often provide several context repos at once.

## Decision

### Components

| Component | File | Purpose |
|---|---|---|
| `RepoChipInput` | `frontend/src/components/RepoChipInput.tsx` | Multi-value chip input for **reference_repos**. Each selected repo renders as a removable chip. Dropdown shows filtered suggestions from recent repos. |
| `RepoSuggestInput` | `frontend/src/components/RepoSuggestInput.tsx` | Single-value autocomplete input for **repo_path**. Dropdown shows filtered suggestions from recent repos. |
| `useRecentRepos` | `frontend/src/hooks/useRecentRepos.ts` | localStorage-backed hook managing a shared list of recently used repos. Powers suggestions for both components. |

### Data flow

```
App.tsx
  └─ useRecentRepos() → { recentRepos, addRepo }
       │
       ├─ SubmissionForm (recentRepos prop)
       │    ├─ RepoSuggestInput  (repo_path field, suggestions=recentRepos)
       │    └─ RepoChipInput     (reference_repos field, suggestions=recentRepos)
       │
       └─ ScheduleCard (recentRepos prop)
            ├─ RepoSuggestInput  (repo_path field)
            └─ RepoChipInput     (reference_repos field)
```

### RepoChipInput behavior

- Type a repo name, press **Enter**, **Tab**, or **comma** to add it as a chip
- Click **x** on a chip to remove it
- **Backspace** on an empty input removes the last chip
- Arrow keys navigate the suggestion dropdown; Escape closes it
- Already-selected repos are excluded from suggestions
- Max 8 suggestions shown at a time

### RepoSuggestInput behavior

- Typing filters the suggestion dropdown by substring match
- Arrow keys navigate suggestions; Enter selects the highlighted one
- Escape closes the dropdown
- `autoComplete="off"` prevents browser autofill interference

### useRecentRepos storage

- **localStorage key:** `hh_recent_repos`
- **Max entries:** 20
- **Ordering:** most recently used first (deduped on add)
- **Cross-tab sync:** listens to the `storage` event so multiple tabs stay in sync
- **Graceful degradation:** silently ignores quota-exceeded errors

### Form state serialization

`reference_repos` is stored as a comma-separated string in `FormState`. `SubmissionForm` splits it into an array for `RepoChipInput` and joins back on change:

```typescript
const referenceChips = form.reference_repos.split(",").map(s => s.trim()).filter(Boolean);
const setReferenceChips = (repos: string[]) => onFieldChange("reference_repos", repos.join(", "));
```

## Alternatives considered

- **Plain text inputs** — simpler but poor UX for multi-repo selection and no memory of past repos
- **Server-side repo history** — adds backend complexity; localStorage is sufficient since repos are user-local preferences
- **IndexedDB** — overkill for a small string list; localStorage is simpler and has better browser support

## Consequences

- Users get fast repo entry via autocomplete and don't need to remember exact `owner/repo` strings
- The chip UI makes it clear which reference repos are selected and easy to add/remove them
- Recent repos persist across sessions and sync across tabs without any backend support
- Both `SubmissionForm` and `ScheduleCard` share the same suggestion pool
