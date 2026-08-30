---
name: server-report
description: Report live host capacity and per-project session usage, including CPU, memory, swap, disk, OOM events, and process sprawl. Use when asked about machine load, capacity, resource consumers, or whether another session will fit.
---

# Report host capacity

Read `.claude/skills/server-report/SKILL.md` completely and follow it as the canonical shared
procedure. From the project root, run the same implementation Claude uses:

```bash
python3 .claude/skills/server-report/report.py
```

Forward supported options such as `--sample=5` or `--az` only as described there. The report is
probe-based and read-only; do not infer the host from its name or substitute remembered capacity.
