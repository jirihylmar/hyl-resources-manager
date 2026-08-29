---
name: check-aws
description: Verify a syndicate project's declared AWS account, region and resources against live read-only evidence. Use when starting AWS work, checking deployment state, or validating resources; never infer identity from an MCP server or profile nickname.
---

# Check AWS

Read `.claude/commands/check-aws.md` completely and execute it as the canonical procedure, translating
Claude tool names and MCP handles to capabilities actually available in this Codex session. Verify
the account number before other calls. Preserve read-only posture unless the user's task explicitly
authorizes a write, and never persist host-specific profile/server names in travelling project files.
