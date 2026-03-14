# Pre-Landing PR Review

Analyze the current branch's diff against main for structural issues that tests don't catch. Two-pass review: Pass 1 (CRITICAL) covers SQL & Data Safety, Race Conditions, and LLM Output Trust Boundary. Pass 2 (INFORMATIONAL) covers Conditional Side Effects, Magic Numbers, Dead Code, LLM Prompt Issues, Test Gaps, Crypto & Entropy, Time Safety, Type Coercion, and View/Frontend. Be terse — one line problem, one line fix. Only flag real problems.
