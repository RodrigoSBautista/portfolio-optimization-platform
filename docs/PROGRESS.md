# Progress

> Living checkpoint so any session (or teammate) can resume cleanly after an
> interruption. Keep this current — see [WORKFLOW.md](WORKFLOW.md). Update the
> **Next step** line so a cold start knows exactly what to do next.

_Last updated: 2026-06-10_

## Next step (start here on resume)

- Decide when to begin **Phase 0 (Foundations)**: `git init` + GitHub remote +
  `.gitignore` + `uv` environment. No application code yet.
- **Remote (SSH):** `git@github.com:RodrigoSBautista/portfolio-optimization-platform.git`
  (auth via the local `~/.ssh/id_ed25519` key — confirm it's added to GitHub and
  the repo exists before pushing).

## In progress

- _(nothing in flight)_

## Done

- Project decision docs written: `docs/ARCHITECTURE.md`, `docs/PROMPTS.md`,
  `docs/AGENT_MODELS.md`.
- Standing conventions added: `CLAUDE.md`, `docs/WORKFLOW.md`, this file,
  `.gitignore`.
- Agent-teams enabled; team model config decided (lead + quant-ml on Opus, others
  on Sonnet; plan-before-execute).

## Blocked / open questions

- _(none)_

---

### How to use this file
- **Done** — completed, committed units of work.
- **In progress** — exactly what's mid-flight right now (ideally one thing).
- **Next step** — the single concrete next action to take.
- Update it as you go, and commit it alongside the work it describes.
