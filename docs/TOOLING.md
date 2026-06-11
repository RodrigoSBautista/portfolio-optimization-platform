# Tools & Context Efficiency

Project-specific decisions only. The general Claude Code mechanics (how skills,
subagents, and MCP load) are assumed knowledge — this file records what's
**non-obvious to this project**.

## Creating skills — the team's call

When you (lead or any teammate) notice **reusable domain knowledge or a workflow
repeating** across tasks — e.g. the CAGR / Sharpe / max-drawdown formulas,
rebalancing rules, an optimization technique's steps, or a recurring data-fetch
gotcha — **create a Skill for it** (`.claude/skills/<name>/SKILL.md`) so it loads
on demand instead of bloating prompts or `CLAUDE.md`.

Use your judgment: make a skill when it will genuinely be reused and is worth the
upkeep — don't pre-create skills "just in case," and don't paste the same
instructions repeatedly when a skill would do. Likewise, only enable **MCP servers
/ plugins you actually use** — each one taxes every turn's context.

## Out-of-scope tools (decided 2026-06-11)

This is a **free-data (yfinance), retail portfolio** project, so these finance
plugins/repos are **not adopted** (paid/enterprise and/or wrong domain):

| Tool | Why not |
|---|---|
| `claude.com/plugins/finance` | Corporate accounting (journal entries, close, SOX) — wrong domain |
| `claude.com/plugins/sp-global` · `kensho-technologies/spglobal-agent-skills` | Tear sheets / earnings previews from S&P Capital IQ — paid subscription |
| `anthropics/financial-services` | Enterprise FSI agents wired to paid data MCPs |

**Reference only:** `anthropics/financial-services` is a clean public example of
skill/plugin structure — read it for patterns, not as a dependency.

**Revisit condition:** reconsider the S&P Global / Kensho skills only if paid
**S&P Capital IQ Pro / S&P Global API** access is ever obtained.
