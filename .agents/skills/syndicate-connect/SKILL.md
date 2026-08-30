---
name: syndicate-connect
description: Connect this machine to the syndicate knowledge inbox using an ingest URL and per-host token, proving the route before recording it. Use for a new host or when reporting says NO ROUTE or spool.
---

# Connect this host

Read `.claude/skills/syndicate-connect/SKILL.md` completely before acting; it is the canonical
security and failure contract. With the operator-provided URL and per-host token, run the shared
implementation from the project root:

```bash
bash .claude/skills/syndicate-connect/connect.sh --url <ingest-url> --token <host-token>
```

Never print or persist the token anywhere except through that script. It must prove the token
before writing the machine-level route, and a failed proof must leave no route behind.
