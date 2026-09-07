---
name: overlay-check
description: Validate this project's local-overlay splice anchors against its own delivered command files before a distribution rejects them. Use after editing anything under .claude/local-overlays/, or when a distribution reported broken-overlay.
---

# Check local-overlay anchors

Read `.claude/skills/overlay-check/SKILL.md` completely and apply its canonical rules. Run the
shared checker from the project root:

```bash
python3 .claude/skills/overlay-check/overlay_check.py
```

Exit `0` every anchor binds uniquely, `1` at least one problem, `2` no overlays present.

An anchor that matches zero lines blocks the next distribution for **every project on this host**,
not just this one. An anchor that matches more than one line is resolved first-match-wins and
reports nothing, so the overlay lands somewhere the author did not choose. Do not reproduce or
weaken the checks in Codex prose; this adapter and Claude run the same executable checker.
