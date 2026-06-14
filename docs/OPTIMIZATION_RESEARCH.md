# Optimization Techniques — Ranked Survey (Phase 2)

> **Purpose:** an **unbiased** survey of portfolio-construction techniques so the user
> can **select** before any implementation (per [PHASE2_PLAN.md](PHASE2_PLAN.md)). It
> covers both sub-problems — **Allocation** (weight a fixed, user-chosen set) and
> **Selection** (choose which tickers from a universe). The **equal-weight (1/N)
> baseline is the reference** every method is judged against.
>
> **Educational use only — not financial advice.** Method by Claude using built-in web
> search + domain knowledge (the paid `parallel-deep-research` service was not used by
> user choice). Sources linked inline.

## Our use case → ranking criteria

This app is **long-term (3–5 yr), low-churn, long-only, retail, free daily price data
(yfinance), no fundamentals by default.** Techniques are scored 1–5 (5 = best fit) on:

| Criterion | Why it matters here |
|---|---|
| **Low churn / turnover** | Long-term, low-cost holding — high turnover = trading costs + tax drag. **Weighted heaviest.** |
| **Robustness to estimation error** | Free daily data + short histories make estimates noisy; methods needing **expected-return forecasts** are fragile. |
| **Data/assumption needs** | Prefer methods needing only **price history** (no fundamentals, no return forecasts, no market caps). |
| **Implementation + library maturity** | Mature, well-tested Python libs (PyPortfolioOpt, riskfolio-lib, skfolio, scikit-learn) lower risk. |
| **Out-of-sample evidence** | Does it actually beat 1/N net of costs in published studies? |
| **Interpretability** | Retail users should understand the suggestion. |

**The headline finding that frames everything:** DeMiguel, Garlappi & Uppal (2009),
*Optimal Versus Naive Diversification*, tested 14 optimization models on 7 datasets and
found **none consistently beat 1/N** on Sharpe, certainty-equivalent return, or turnover
out-of-sample — the estimation error in "optimal" inputs more than offsets the
theoretical gains. So **equal-weight is a genuinely strong baseline**, and methods that
**avoid estimating expected returns** (risk-based methods) tend to be the robust ones.
([DeMiguel et al. 2009, RFS](https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901) ·
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1376199))

---

## Part A — Allocation techniques (weight a fixed set)

### A0. Equal weight (1/N) — the baseline *(always implemented)*
- **How:** every holding gets `1/N`.
- **Inputs:** none (just the ticker count). **Turnover:** ~zero (only drift
  rebalancing). **Libraries:** trivial. **Fit:** allocation.
- **Pros:** zero estimation error, maximally robust, transparent; hard to beat OOS.
  **Cons:** ignores risk/correlation — concentrates risk in volatile names.
- **Failure modes:** none statistical; just not risk-aware.

### A1. Inverse-volatility weighting
- **How:** weight ∝ `1 / volatility_i`; lower-vol assets get more. Needs only each
  asset's volatility (a long lookback, e.g. 1–3 yr).
- **Turnover:** **low** (vols are stable, especially with a long window). **Robustness:**
  high (no correlations, no return forecasts). **Libraries:** trivial / riskfolio-lib.
- **Pros:** simple, robust, low-churn, risk-aware-ish. **Cons:** ignores correlations
  (not true diversification). **Fit:** allocation.

### A2. Risk parity / Equal Risk Contribution (ERC)
- **How:** weights set so **each asset contributes equal risk** to the portfolio (uses
  the covariance matrix). Generalizes inverse-vol by accounting for correlations.
- **Turnover:** **low–moderate** (empirically among the lowest of the optimizers — one
  study cites ~5% vs HRP's ~18%, [QuantPedia/HRP](https://quantpedia.com/hierarchical-risk-parity/)).
  **Robustness:** high (no expected returns). **Libraries:** riskfolio-lib, PyPortfolioOpt.
- **Pros:** well-diversified by risk, robust, low-churn, strong practitioner track record.
  **Cons:** needs a covariance matrix (solvable); less intuitive than 1/N. **Fit:** allocation.

### A3. Hierarchical Risk Parity (HRP) — López de Prado (2016)
- **How:** clusters assets by correlation (a dendrogram), then allocates capital by
  **recursively splitting risk equally down the tree** — no matrix inversion required.
- **Turnover:** **moderate** (rebalances can shift with the clustering; ~18% in one
  study — higher than plain risk parity). **Robustness:** **high** — designed to avoid
  unstable covariance-inversion; lower OOS variance than classical min-variance (CLA) in
  López de Prado's Monte Carlo tests. **Libraries:** PyPortfolioOpt, riskfolio-lib, skfolio.
- **Pros:** modern, robust to ill-conditioned covariances, good diversification, doesn't
  need a positive-definite matrix. **Cons:** more moving parts (linkage/clustering
  choices); moderate turnover. **Fit:** allocation **and** informs selection (clusters).
  ([López de Prado 2016, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678) ·
  [Wikipedia: HRP](https://en.wikipedia.org/wiki/Hierarchical_Risk_Parity))

### A4. Minimum-variance (ideally with Ledoit-Wolf shrinkage)
- **How:** solve for the lowest-variance long-only portfolio from the covariance matrix.
  **Ledoit-Wolf shrinkage** stabilizes the covariance estimate (PyPortfolioOpt wraps it).
- **Turnover:** **moderate–high** (sensitive to covariance changes → weights move).
  **Robustness:** moderate (better with shrinkage; no expected returns needed — a plus).
  **Libraries:** PyPortfolioOpt, riskfolio-lib.
- **Pros:** directly minimizes risk; strong low-vol tilt; no return forecasts. **Cons:**
  can concentrate in a few low-vol names; estimation-error sensitive without shrinkage;
  higher churn. **Fit:** allocation.

### A5. Maximum diversification
- **How:** maximize the ratio of weighted-average vol to portfolio vol (the
  "diversification ratio"). Risk-based, no return forecasts.
- **Turnover:** moderate. **Robustness:** moderate (covariance-dependent). **Libraries:**
  riskfolio-lib. **Pros:** explicitly targets diversification. **Cons:** similar
  estimation sensitivity to min-variance; less common. **Fit:** allocation.

### A6. Mean-variance / Markowitz (max Sharpe / efficient frontier)
- **How:** trade off **expected return** vs variance on the efficient frontier.
- **Turnover:** **high** (very sensitive to expected-return inputs → unstable weights).
  **Robustness:** **low** — needs expected-return estimates, the single biggest source of
  OOS failure (the DeMiguel result). **Libraries:** PyPortfolioOpt, riskfolio-lib.
- **Pros:** the theoretical foundation; flexible. **Cons:** fragile out-of-sample,
  high churn, error-maximizing without heavy shrinkage. **Fit:** allocation. **Lower fit
  here** precisely because of the expected-return dependence.

### A7. Black-Litterman
- **How:** blends a market-equilibrium prior (from market-cap weights) with the user's
  **subjective views** to produce posterior expected returns, then optimizes.
- **Turnover:** moderate–high. **Robustness:** moderate (more stable than raw MVO) **but**
  needs **market caps + explicit views** — extra data and user input we don't have by
  default. **Libraries:** PyPortfolioOpt. **Pros:** principled way to add views; stable
  vs naive MVO. **Cons:** heaviest data/assumption load; overkill for a free-data retail
  tool with no view-elicitation UI. **Fit:** allocation. **Lower fit here.**

### Allocation ranking (fit for THIS use case)

| Rank | Method | Churn | Robust | Data needs | Libs | Overall fit |
|---|---|---|---|---|---|---|
| — | **Equal weight (1/N)** *(baseline)* | 5 | 5 | 5 | 5 | **Baseline** |
| 1 | **Risk parity / ERC** | 5 | 5 | 4 | 5 | ★★★★★ |
| 2 | **Inverse-volatility** | 5 | 5 | 5 | 5 | ★★★★☆ (simplest robust upgrade) |
| 3 | **HRP** | 3 | 5 | 4 | 5 | ★★★★☆ (most modern/robust) |
| 4 | **Min-variance + shrinkage** | 3 | 4 | 4 | 5 | ★★★☆☆ |
| 5 | **Max diversification** | 3 | 3 | 4 | 4 | ★★★☆☆ |
| 6 | **Mean-variance / Markowitz** | 1 | 2 | 3 | 5 | ★★☆☆☆ |
| 7 | **Black-Litterman** | 2 | 3 | 1 | 4 | ★★☆☆☆ |

---

## Part B — Selection techniques (choose which tickers from a universe)

### B1. Low-volatility screen
- **How:** rank the candidate universe by **long-window volatility**, keep the lowest-vol
  `k`. Pair with a risk-based allocator.
- **Turnover:** **low** (long-window vol is stable; using 3-yr vol "implies much lower
  portfolio turnover," [INTECH white paper](https://17eb94422c7de298ec1b-8601c126654e9663374c173ae837a562.ssl.cf1.rackcdn.com/Documents/INTECH/White%20Papers/The%20Low-Volatility%20Anomaly%20Not%20So%20Anomalous%20After%20All.pdf)).
  **Evidence:** the **low-volatility anomaly** — low-vol stocks have historically matched
  or beaten high-vol stocks over the long run with less risk, across 90+ years
  ([Wikipedia: low-volatility investing](https://en.wikipedia.org/wiki/Low-volatility_investing) ·
  [CFA Institute](https://blogs.cfainstitute.org/investor/2024/02/16/the-low-volatility-factor-and-occams-razor/)).
  **Data:** prices only. **Fit:** selection. **Strong fit** for low-churn long-term.

### B2. Correlation / clustering-based selection
- **How:** cluster the universe by correlation (the same dendrogram HRP uses, or k-means
  on returns), then pick representatives from each cluster to maximize diversification.
- **Turnover:** low–moderate (clusters are fairly stable with long windows).
  **Data:** prices only. **Libraries:** scikit-learn, scipy, riskfolio-lib. **Pros:**
  directly targets diversification; pairs naturally with HRP. **Cons:** clustering choices
  (linkage/`k`) affect results. **Fit:** selection (+ synergy with HRP allocation).

### B3. Quality / fundamental screen
- **How:** screen on fundamentals (profitability, low debt, earnings stability).
- **Turnover:** **low** (fundamentals change slowly) and **trades cheaply**
  ([Research Affiliates](https://www.researchaffiliates.com/insights/publications/articles/637-can-momentum-investing-be-saved)).
  **Data:** **requires fundamentals** — not in our free price-only data layer by default
  (yfinance fundamentals are spotty). **Fit:** selection. Good economics, **but a data
  dependency we'd have to add.**

### B4. Momentum / trend screen
- **How:** keep recent winners (e.g. top `k` by trailing 6–12 month return).
- **Turnover:** **high** — "momentum strategies are characterized by high turnover and
  high trading costs"; premiums are "considerably diminished by trading costs"
  ([Research Affiliates](https://www.researchaffiliates.com/insights/publications/articles/637-can-momentum-investing-be-saved) ·
  [Alpha Architect](https://alphaarchitect.com/low-volatility-strategies/)). **Data:**
  prices only. **Fit:** selection. **Poor fit** for a *low-churn* mandate (it's the
  highest-churn factor), though strong as a return signal.

### Selection ranking (fit for THIS use case)

| Rank | Method | Churn | Data we have? | Evidence | Overall fit |
|---|---|---|---|---|---|
| 1 | **Low-volatility screen** | 5 | ✅ prices only | strong, long-run | ★★★★★ |
| 2 | **Correlation/clustering** | 4 | ✅ prices only | diversification | ★★★★☆ |
| 3 | **Quality/fundamental** | 5 | ❌ needs fundamentals | strong | ★★★☆☆ (data gap) |
| 4 | **Momentum/trend** | 1 | ✅ prices only | strong signal, costly | ★★☆☆☆ (high churn) |

---

## Recommendation shortlist (the choice is yours)

Framed against the **equal-weight baseline** (always implemented):

- **Allocation — top candidates** (all avoid fragile expected-return forecasts):
  1. **Risk parity / ERC** — best all-round fit (robust, low-churn, diversified).
  2. **HRP** — most modern/robust to covariance noise; great story for a portfolio piece.
  3. **Inverse-volatility** — the simplest robust upgrade over 1/N.
  4. **Min-variance + Ledoit-Wolf shrinkage** — if maximal risk reduction is the goal
     (accepting more churn/concentration).
- **Selection — top candidates:**
  1. **Low-volatility screen** — best fit (low churn, prices-only, strong long-run record).
  2. **Correlation/clustering** — pairs beautifully with HRP allocation.

**A natural, coherent pairing** for "long-term, low-churn, prices-only": **HRP (or risk
parity) for allocation + a low-volatility or clustering screen for selection**, always
shown beside equal-weight. But this is a menu, not a verdict — **you pick**.

**Libraries:** [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) (MVO,
Black-Litterman, HRP, shrinkage), [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib)
(24 risk measures, risk parity, HRP), [skfolio](https://github.com/skfolio/skfolio)
(scikit-learn-style), and **scikit-learn/scipy** (clustering, Ledoit-Wolf). All are
mature and pip-installable.

## Sources
- [DeMiguel, Garlappi & Uppal (2009), *Optimal Versus Naive Diversification*, RFS](https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901) ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1376199))
- [López de Prado (2016), *Building Diversified Portfolios that Outperform Out-of-Sample* (HRP), SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678) · [Wikipedia: Hierarchical Risk Parity](https://en.wikipedia.org/wiki/Hierarchical_Risk_Parity) · [QuantPedia: HRP](https://quantpedia.com/hierarchical-risk-parity/)
- [Wikipedia: Low-volatility investing](https://en.wikipedia.org/wiki/Low-volatility_investing) · [CFA Institute: The Low-Volatility Factor and Occam's Razor](https://blogs.cfainstitute.org/investor/2024/02/16/the-low-volatility-factor-and-occams-razor/) · [INTECH: The Low-Volatility Anomaly](https://17eb94422c7de298ec1b-8601c126654e9663374c173ae837a562.ssl.cf1.rackcdn.com/Documents/INTECH/White%20Papers/The%20Low-Volatility%20Anomaly%20Not%20So%20Anomalous%20After%20All.pdf)
- [Research Affiliates: Can Momentum Investing Be Saved?](https://www.researchaffiliates.com/insights/publications/articles/637-can-momentum-investing-be-saved) · [Alpha Architect: low-volatility strategies](https://alphaarchitect.com/low-volatility-strategies/)
- Libraries: [PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt) · [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) · [skfolio](https://github.com/skfolio/skfolio)
