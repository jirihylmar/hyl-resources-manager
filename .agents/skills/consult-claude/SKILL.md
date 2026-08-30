---
name: consult-claude
description: Have Claude independently review a tracked project task or phase while Codex remains the author and orchestrator, then reconcile the bounded review into the consult ledger. Use when Codex should consult Claude as the second reader.
---

# Consult Claude from Codex

Use the installed `$syndicate-consult-claude` host skill for this task. It is the Codex-side
orchestrator for the distributed consult procedure and is installed by:

```bash
bash .claude/skills/consult-codex/prepare-host.sh --apply
```

Before opening a cycle, read `.claude/skills/consult-codex/SKILL.md` completely. That project file
is the canonical procedure and digest authority; `consult-codex` is its Claude-facing name, while
this skill is its role-reversed Codex entry. Preserve all of its bounds: review a named task or
phase from a transient clone of committed HEAD, keep `progress.json` read-only during consultation,
record every opening and closing outcome in `consult_notes.md`, and stop after at most three
author/reviewer rounds.

If `$syndicate-consult-claude` is unavailable or its expected procedure digest differs, refuse with
`HOST-NOT-PREPARED` or `PROCEDURE-DRIFT` as the canonical procedure specifies. Do not improvise a
second consult implementation in this adapter.
