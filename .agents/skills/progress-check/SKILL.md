---
name: progress-check
description: Validate progress.json for destructive corruption, append-only violations, and missing authorship or assignment metadata. Use before committing progress changes or when investigating malformed, missing, changed, or unattributed work.
---

# Check progress state

Read `.claude/skills/progress-check/SKILL.md` completely and apply its canonical rules. Run the
shared checker from the project root:

```bash
python3 .claude/skills/progress-check/progress_check.py
python3 .claude/skills/progress-check/progress_check.py --staged
python3 .claude/skills/progress-check/progress_check.py --base none
```

Choose the mode described by the canonical skill. Do not reproduce or weaken its validation in
Codex prose; this adapter and Claude use the same executable checker.
