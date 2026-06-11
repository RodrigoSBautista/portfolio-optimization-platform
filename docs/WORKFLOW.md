# Workflow — Version Control & Resume-from-Interruption

The detailed reference behind the summary in [../CLAUDE.md](../CLAUDE.md). Applies
to every phase and every teammate.

---

## 1. Version control setup (Phase 0)

Do this once, before feature work:

```bash
# from the project root
git init
uv init                 # or `uv venv` — establish the UV-managed environment
# create .gitignore (already seeded in this repo) before the first add
git add -A
git commit -m "chore: project scaffold + conventions"

# GitHub remote (from the start)
gh repo create <name> --private --source=. --remote=origin --push
# or, manually:
# git remote add origin git@github.com:<user>/<name>.git
# git push -u origin main
```

> Requires the GitHub CLI (`gh auth login`) or an SSH key configured for GitHub.

### `.gitignore` essentials (see [/.gitignore](../.gitignore))

Never commit: `.env` and any secrets, the SQLite database (`*.db`, `*.sqlite3`),
parquet/price **data caches**, `__pycache__/`, `.venv/`, `.ipynb_checkpoints/`.
Run `git status` before every commit to confirm none are staged.

## 2. Commit discipline

- **Small and frequent.** One logical change per commit; commit after each
  meaningful unit of work. Uncommitted work is work that can be lost.
- **Clear messages.** Conventional style is encouraged:
  `feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`.
- **Feature branches.** Branch per feature/layer (e.g. `feat/data-layer`,
  `feat/core-simulation`); merge to `main` via PR once green. Keep `main` working.
- **Secrets never land in git.** If one slips in, rotate it — don't just delete
  the line.
- **Auto-checkpoints.** A `Stop` hook (`.claude/hooks/auto-commit.ps1`) commits +
  pushes a timestamped `chore: checkpoint` at most once every ~10 min when the
  tree is dirty — a safety net against interruptions, **not** a replacement for
  meaningful, well-messaged commits at logical milestones. Review or disable it
  via `/hooks`; change the cadence by editing the `10 minutes ago` throttle in the
  script.

## 3. Resume-from-interruption playbook

A session can stop mid-task because of token, context, or usage limits. The goal:
**lose at most one small task, and resume cleanly.**

### While working
- Commit after each meaningful unit (this is the primary safety net).
- Keep [PROGRESS.md](PROGRESS.md) current — move items between
  **Done / In progress / Next step** as you go, and write the *single concrete
  next action* so a cold start knows exactly where to pick up.
- Size tasks small, each with a clear "definition of done". Avoid giant
  half-finishable steps.

### When resuming a fresh session
1. Read [PROGRESS.md](PROGRESS.md) — what's done, what's mid-flight, what's next.
2. Read `git log --oneline -n 20` and `git status` — confirm what actually landed.
3. Continue from the *Next step*; update PROGRESS.md as you go.

### In agent teams
- The **shared task list persists across sessions** — the lead and teammates
  resume from it after a restart. Keep task statuses accurate (claimed / in
  progress / done) so the picture survives an interruption.
- The lead breaks work into small, independently-completable tasks for the same
  reason.

## 4. Quick checklist

- [ ] `.gitignore` excludes secrets, `*.db`, and data caches before first commit
- [ ] Committing after each meaningful unit, with clear messages
- [ ] `docs/PROGRESS.md` reflects reality, including the next concrete step
- [ ] Tasks are small and atomic
- [ ] (Teams) shared task list statuses are accurate
