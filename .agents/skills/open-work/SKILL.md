---
name: open-work
description: Render current, stuck, and deferred work from progress.json using the project’s canonical deterministic renderer. Use for session handoffs, progress summaries, or questions about open work.
---

# Render open work

Read `.claude/skills/open-work/SKILL.md` completely, then follow it as the canonical shared
procedure. Run its implementation from the project root:

```bash
python3 .claude/skills/open-work/open_work.py
```

Pass `--file <path>` when the user names another progress file. Preserve the canonical rule:
the script determines which rows exist; replace every emitted `<FILL: …>` token with a concise
plain-language explanation before showing the result. This adapter contains no separate renderer.
