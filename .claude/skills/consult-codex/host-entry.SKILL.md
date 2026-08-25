---
name: syndicate-consult-claude
description: Run the consult loop from Codex (Entry A) — you are the orchestrator; spawn the nested reviewer and the Claude author for the project you are in, following the distributed consult-codex procedure. Refuses if the project's copy of that procedure has drifted from the one this entry was installed against.
---

# syndicate-consult-claude — Entry A of the consult loop

You are a Codex session running with `--dangerously-bypass-approvals-and-sandbox` inside one of
the operator's playbook projects. This entry does **not** contain the procedure; it points at the
one copy every project carries and refuses to run against a different one.

Installed by `prepare-host.sh` from the `consult-codex` skill on {{INSTALLED_AT}}.
Expected procedure digest: `{{DIGEST}}` — sha256 of the block between
`<!-- procedure:begin -->` and `<!-- procedure:end -->` in
`.claude/skills/consult-codex/SKILL.md`.

## Do this, in order

1. **Digest check, before anything else.** Run:
   ```bash
   sed -n '/<!-- procedure:begin -->/,/<!-- procedure:end -->/p' .claude/skills/consult-codex/SKILL.md | sha256sum | cut -c1-16
   ```
   If the result is not `{{DIGEST}}`, stop and say `PROCEDURE-DRIFT: host entry expects {{DIGEST}}, project has <value>` — the host was prepared against a different version of the procedure than this project carries. Do not improvise a merge; the operator re-runs `prepare-host.sh` or `/distribute-defaults`.
2. **Read** `.claude/skills/consult-codex/SKILL.md` in full. It is written for the Claude session as author; you are the orchestrator, so the mapping is: every `consult.sh` command it names, you run as a shell command from this project's root; the "author" it addresses is `claude -p --dangerously-skip-permissions --output-format json` (then `--resume <session_id>` per round), which you spawn and whose replies you hand back with `consult.sh respond`.
3. **Never review from this checkout.** The reviewer is the nested `codex exec` that `consult.sh review` starts in the transient clone. You do not read the project as the reviewer; you drive.
4. **Every spawned command** ends with `</dev/null` and is wrapped in `timeout` — a nested agent with an open stdin hangs forever.
5. **The operator's "add it"** is collected at your prompt. Present the Proposed Work table verbatim; add nothing to `progress.json` yourself in any outcome. Only the Claude author, on the operator's word, runs `/add-work`.
6. **Close** with the outcome the log grammar allows. If the reviewer never completed a round, the only honest outcome is `not-reviewed:REVIEWER-FAILED`, and `consult.sh close` will enforce that.

## What you may read but not change

`consult_notes.md` is written only by `consult.sh`. `progress.json` is written only by `/add-work` on the operator's word. This checkout's working tree must be byte-identical when the cycle ends; the posture check will report you if it is not.
