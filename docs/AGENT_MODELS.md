# Agent Teams — How Models & Plan Mode Are Inherited

Reference notes for configuring which model each teammate uses in Claude Code
**agent teams**, and how the "plan before executing" flow works. Sourced from the
official docs ([agent-teams](https://code.claude.com/docs/en/agent-teams),
[model-config](https://code.claude.com/docs/en/model-config),
[sub-agents](https://code.claude.com/docs/en/sub-agents)).

---

## TL;DR

- **Teammates do NOT inherit the lead's model by default.** You must set it
  explicitly (per-agent frontmatter, the spawn prompt, `/config`, or an env var).
- **`opusplan` is NOT a valid teammate model.** It is a *main-session-only* mode
  (Opus while in plan mode → Sonnet for execution). A teammate's plan→execution
  transition is gated by the **lead's approval**, not an automatic model switch,
  so `opusplan` has nothing to hook into. Valid values are `opus`, `sonnet`,
  `haiku`, `inherit`, or a full model ID.
- **Teammates DO have a real plan mode.** They can be required to draft a plan in
  read-only mode and wait for the lead to approve before implementing.

---

## How a teammate's model is decided

Four supported mechanisms (highest-level override last):

| # | Mechanism | How | Accepts `opusplan`? |
|---|---|---|---|
| 1 | **Subagent `model:` frontmatter** | `model:` in `.claude/agents/<name>.md`; honored when that definition is spawned as a teammate | No |
| 2 | **In the spawn prompt** | Tell the lead in natural language, e.g. *"Use Sonnet for each teammate."* | No |
| 3 | **`/config` → Default teammate model** | Sets the fallback when the prompt doesn't specify; choose *"Default (leader's model)"* to make teammates follow the lead | No |
| 4 | **`CLAUDE_CODE_SUBAGENT_MODEL` env var** | Blanket override for **all** subagents/teammates; overrides the per-invocation `model` and the frontmatter. Set to `inherit` for normal resolution | No |

> Key quote: *"Teammates don't inherit the lead's `/model` selection by default.
> To change the model used when the prompt doesn't specify one, set **Default
> teammate model** in `/config`."*

> Per-definition: *"The teammate honors that definition's `tools` allowlist and
> `model`."*

**Recommendation:** use **per-agent frontmatter (#1)** so each engineer can have a
different model. Avoid `CLAUDE_CODE_SUBAGENT_MODEL` unless you want every teammate
forced to one model — it overrides the frontmatter.

---

## Plan mode for teammates

> *"For complex or risky tasks, you can require teammates to plan before
> implementing. The teammate works in read-only plan mode until the lead approves
> their approach… When a teammate finishes planning, it sends a plan approval
> request to the lead. The lead reviews the plan and either approves it or rejects
> it with feedback. If rejected, the teammate stays in plan mode, revises… Once
> approved, the teammate exits plan mode and begins implementation."*

This gives a powerful pattern: **the Opus lead reviews every Sonnet teammate's
plan before any code is written** — Opus-level judgment over all planning, while
execution stays on cheaper Sonnet.

---

## This project's chosen configuration

| Role | Where | Model | Rationale |
|---|---|---|---|
| **Team lead** (orchestrating session) | `.claude/settings.json` → `"model": "opus"` | **Opus** | Heaviest reasoning: architecture, coordination, reviewing/approving teammate plans |
| **quant-ml-engineer** | `.claude/agents/quant-ml-engineer.md` → `model: opus` | **Opus** | Finance/ML correctness is subtle and high-stakes |
| **backend-data-engineer** | `…/backend-data-engineer.md` → `model: sonnet` | **Sonnet** | Solid execution work; cheaper/faster |
| **frontend-viz-engineer** | `…/frontend-viz-engineer.md` → `model: sonnet` | **Sonnet** | UI build-out; cheaper/faster |
| **devops-qa-engineer** | `…/devops-qa-engineer.md` → `model: sonnet` | **Sonnet** | Tooling/CI/tests; cheaper/faster |

**Plan-before-execute:** every teammate is instructed to produce a short plan and
wait for the lead's approval before implementing (read-only plan mode → lead
approval). The Opus lead vets each plan.

**Why not `opusplan` anywhere:** it only works for the main session, and even
there it would switch the *lead* to Sonnet during execution — but we want the lead
on Opus throughout for reviewing plans, so we set the lead to plain `opus`.

---

## How to change it later

- Make a teammate use Opus: set `model: opus` in its `.claude/agents/*.md`.
- Force every teammate to one model temporarily: `CLAUDE_CODE_SUBAGENT_MODEL=opus`
  (or `sonnet`) in `.claude/settings.json` `env` (overrides all frontmatter).
- Make teammates follow the lead: `/config` → Default teammate model → *Default
  (leader's model)*.
