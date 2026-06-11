# CLAUDE.md — Standing Project Conventions

> Loaded into context every session. These rules **always apply** — to the team
> lead and to every teammate, in every phase. Keep them short; details live in
> [docs/WORKFLOW.md](docs/WORKFLOW.md).

## What this project is

An investment portfolio simulation & optimization platform (Python): simulate how
money would have grown if invested in chosen US stocks/ETFs from a past date,
track saved portfolios daily vs a benchmark (each user sees only their own), and
suggest long-term optimized portfolios. Built in phases: local Streamlit + SQLite
→ portfolio optimization → professional React + PostgreSQL.

**Key docs:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (tooling & rationale) ·
[docs/PROMPTS.md](docs/PROMPTS.md) (build prompts) ·
[docs/AGENT_MODELS.md](docs/AGENT_MODELS.md) (team models) ·
[docs/WORKFLOW.md](docs/WORKFLOW.md) (git + resume playbook) ·
[docs/TOOLING.md](docs/TOOLING.md) (tools & context efficiency) ·
`docs/PLAN.md` (the executable plan, once created).

## Version control (always)

- Git from day one, with a **GitHub remote**.
- **Commit small and often** — after each meaningful unit of work — with clear,
  descriptive messages. Don't let uncommitted work pile up.
- Work on **feature branches**; keep `main` working.
- **Never commit** secrets/`.env`, the SQLite `*.db`, or parquet data caches —
  they're in `.gitignore`. Check `git status` before committing.

## Resume-from-interruption (always)

Work must survive a session stopping mid-way (token / context / usage limits).
This is a permanent practice, not a one-time setup:

1. **Commit after each meaningful unit** so nothing is lost when a session ends.
2. **Keep [docs/PROGRESS.md](docs/PROGRESS.md) current** — update its
   *Done / In progress / Next step* sections as you go.
3. **Break work into small atomic tasks**, each with a clear "definition of done",
   so an interruption costs at most one small task.
4. **To resume a fresh session:** read `docs/PROGRESS.md` and `git log` first to
   recover state before doing anything else.
5. **In agent teams:** use the shared task list — it persists task state across
   sessions, so the lead and teammates can pick up where they left off.

## Team models & planning

Lead + `quant-ml-engineer` run on **Opus**; `backend-data-engineer`,
`frontend-viz-engineer`, `devops-qa-engineer` run on **Sonnet**. Every teammate
**plans before executing** (read-only plan mode → lead approval). Details in
[docs/AGENT_MODELS.md](docs/AGENT_MODELS.md).

## Architecture guardrail

Keep all finance/ML logic **framework-free** in `core/` (no Streamlit/React
imports) so the UI can be swapped later without rewriting logic. Layers:
`data/ · core/ · storage/ · app/ · jobs/ · tests/`.

## Tools & context efficiency

When reusable domain knowledge or a workflow starts repeating, **create a Skill**
for it (loads on demand) instead of bloating prompts or this file — lead and
teammates decide when it's worth it. Only enable MCP servers/plugins you actually
use. This is a free-data (yfinance) project: the paid/enterprise finance plugins
(S&P Global/Kensho, `anthropics/financial-services`, the accounting `finance`
plugin) are **out of scope**. Details: [docs/TOOLING.md](docs/TOOLING.md).
