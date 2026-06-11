# Tools & Context Efficiency

How we add tools and instructions **without wasting tokens on repeated, always-on
context**. The core idea is **progressive disclosure** — pay for context only when
it's actually relevant.

---

## Where each kind of thing belongs

| Kind of thing | Put it in | Why it's efficient |
|---|---|---|
| **Always-true, short rules** (our conventions) | `CLAUDE.md` | Loaded every session — so keep it tiny; only universal rules |
| **Domain knowledge used *sometimes*** (metric formulas, rebalancing rules, optimization notes, data-source gotchas) | a **Skill** (`.claude/skills/<name>/SKILL.md`) | Only the one-line `description` sits in the always-loaded listing; the full body loads **only when a task matches** |
| **Heavy, role-specific context** | a **subagent** (`.claude/agents/*.md`) | Costs tokens only while that agent runs, not on the main thread |
| **Live data/tool access you'll *really* use** | an **MCP server** | Tool definitions cost context **every turn** — so only enable servers you actually use |
| **Everything else** (design rationale, deep reference) | `docs/*.md` | Read **on demand** (e.g. "read docs/ARCHITECTURE.md"), never auto-loaded |

**Rule of thumb:** always-true + short → `CLAUDE.md`; sometimes-needed knowledge →
a **Skill**; heavy role context → a **subagent**; data you'll really use → an
**MCP**; everything else → `docs/` read on demand.

## For this project

- Reusable finance know-how (CAGR / Sharpe / max-drawdown formulas, rebalancing
  rules, optimization technique notes) should live in a **local Skill the
  `quant-ml-engineer` triggers** — **not** pasted into prompts or `CLAUDE.md`.
- Don't pre-load instructions "just in case." If it isn't needed most turns, it
  belongs behind a Skill description or in a `docs/` file read on demand.
- Don't enable MCP servers or plugins you aren't actively using — each one taxes
  every turn's context.

## Out-of-scope tools (decided 2026-06-11)

This is a **free-data (yfinance), retail portfolio** project, so the following
finance plugins/repos are **not adopted** — they are paid/enterprise and/or the
wrong domain, and would add cost, mismatch, and context bloat:

| Tool | Why not |
|---|---|
| `claude.com/plugins/finance` | Corporate **accounting** (journal entries, month-end close, SOX) — wrong domain |
| `claude.com/plugins/sp-global` · `kensho-technologies/spglobal-agent-skills` | Tear sheets / funding digests / earnings previews from **S&P Capital IQ** — require a **paid** S&P subscription |
| `anthropics/financial-services` | Enterprise FSI agents (pitch decks, DCF/LBO/comps, GL recon, KYC) wired to **paid** data MCPs |

**Reference value only:** `anthropics/financial-services` is a clean public
example of how to structure skills/agents/plugins — worth reading for *patterns*,
not as a dependency.

**Revisit condition:** only reconsider the **S&P Global / Kensho** skills if paid
**S&P Capital IQ Pro / S&P Global API** access is ever obtained. Until then, free
yfinance is the data source.
