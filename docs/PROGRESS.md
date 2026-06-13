# Progress

> Living checkpoint so any session (or teammate) can resume cleanly after an
> interruption. Keep this current — see [WORKFLOW.md](WORKFLOW.md). Update the
> **Next step** line so a cold start knows exactly what to do next.

_Last updated: 2026-06-13_

## Next step (start here on resume)

- Begin **Phase 1, step 2** (data layer, owner: backend-data): `data/provider.py`
  (yfinance wrapper, dividend-adjusted / total-return prices) + `data/cache.py`
  (parquet cache + "last refreshed"); handle delisted/non-overlapping/holidays;
  unit-tested. See `docs/PLAN.md §4`.
- **Remote (SSH):** `git@github.com:RodrigoSBautista/portfolio-optimization-platform.git`

## In progress

- _(nothing in flight)_

## Done

- **Phase 1 · step 1 — env scaffold** (branch `feat/env-scaffold`): uv project
  (`pyproject.toml` requires-python >=3.11, `uv.lock` committed), runtime + dev deps,
  layered framework-free skeleton (`data/ core/ storage/ app/ jobs/ tests/`),
  `core/constants.py` (disclaimer + default benchmark), ruff + pytest config (green,
  6 smoke tests), `.env.example` (un-ignored), README run instructions. uv installed
  to `C:\Users\edu_s\.local\bin`.
- **Prompt 2 — four reusable subagents created** in `.claude/agents/`:
  `quant-ml-engineer`, `backend-data-engineer`, `frontend-viz-engineer`,
  `devops-qa-engineer` (all `model: opus`, plan-before-execute, standing
  conventions). Role refinements from `docs/PLAN.md`: quant-ml treats Monte
  Carlo/PCA/forecasting as research-selected candidates (no pre-bias) and gets the
  `Skill` tool for `parallel-deep-research`; auth, client-side save, and
  refresh-vs-cron boundaries made explicit across agents.
- **Prompt 1 — executable plan written** to `docs/PLAN.md` (phased breakdown,
  schema, per-phase DoD/verification). Confirmed this session: Phase 1 = plain
  Streamlit + local SQLite (Supabase deferred to Production); persistence via
  client-side file export/import + optional account save; optimization stays
  unbiased/research-first (no pre-named techniques).
- **Phase 0:** git repo initialized, SSH auth working, first commit pushed to
  `origin/main` (merged with the remote's LICENSE/README).
- Project decision docs written: `docs/ARCHITECTURE.md`, `docs/PROMPTS.md`,
  `docs/AGENT_MODELS.md`.
- Standing conventions added: `CLAUDE.md`, `docs/WORKFLOW.md`, this file,
  `.gitignore`.
- Agent-teams enabled; team model config decided (lead + quant-ml on Opus, others
  on Sonnet; plan-before-execute).
- Tooling policy set (`docs/TOOLING.md`): progressive disclosure; paid/enterprise
  finance plugins (S&P Global/Kensho, anthropics/financial-services, accounting
  `finance`) ruled out of scope for this free-data project.

## Blocked / open questions

- _(none)_

---

### How to use this file
- **Done** — completed, committed units of work.
- **In progress** — exactly what's mid-flight right now (ideally one thing).
- **Next step** — the single concrete next action to take.
- Update it as you go, and commit it alongside the work it describes.
