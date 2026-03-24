# Based on OpenAI's Harness Engineering [Blog Post](https://openai.com/index/harness-engineering/)

```
Iterate with this example structure:
AGENTS.md
ARCHITECTURE.md
INTENT.md
WAITING_ON.md
docs/
├── design-docs/
│   ├── index.md
│   ├── core-beliefs.md
│   └── ...
├── exec-plans/
│   ├── active/
│   ├── completed/
│   └── tech-debt-tracker.md
├── generated/
│   └── db-schema.md
├── product-specs/
│   ├── index.md
│   ├── new-user-onboarding.md
│   └── ...
├── references/
│   ├── design-system-reference-llms.txt
│   ├── nixpacks-llms.txt
│   ├── uv-llms.txt
│   └── ...
├── DESIGN.md
├── FRONTEND.md
├── PLANS.md
├── PRODUCT_SENSE.md
├── QUALITY_SCORE.md
├── RELIABILITY.md
└── SECURITY.md
INTENT.md contains users' intents and desires.
Create an active plan if one does not exist. Continue executing the active plan. If there is nothing more to do, move the plan to completed. Consolidate previous days into completed/20XX-MM-DD.md. Consolidate previous weeks into 2026/Week-X.md.
```

## Additional Action Commands

```

> Go through the git history and populate previous activity reports

> Implement the most actionable/self contained improvements. Always update docs and add testing. Do not add excessive testing, seek >80% and semantically meaningful tests. 
```