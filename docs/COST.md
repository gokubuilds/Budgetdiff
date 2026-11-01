# BudgetDiff — LLM Cost & Token Economics

## 1. Configured Models & Pricing Assumptions

BudgetDiff uses a resilient dual-model architecture with **Google Gemini**. Costs are computed using the configured project pricing rates per million tokens:

| Role | Model Identifier | Input Rate (per 1M tokens) | Output Rate (per 1M tokens) | Rate per Input Token | Rate per Output Token |
|---|---|---|---|---|---|
| **Primary** | `gemini-1.5-pro` | $3.50 | $10.50 | $0.00000350 | $0.00001050 |
| **Fallback** | `gemini-1.5-flash` | $0.075 | $0.30 | $0.000000075 | $0.00000030 |

### Cost Calculation Formula

$$\text{Cost (USD)} = (\text{Prompt Tokens} \times \text{Input Rate}) + (\text{Completion Tokens} \times \text{Output Rate})$$

Every completed query writes its exact financial cost and token breakdown to:
- Persistent SQLite / PostgreSQL database table: `usage_logs`
- Append-only audit log: `logs/cost.jsonl`

---

## 2. Average Token Estimates per Question

Based on Union Budget queries (e.g. comparing PM-KISAN, Samagra Shiksha, or MGNREGS allocations across BE, RE, and Actuals):

- **Average Input Tokens**: 500 tokens (user question + system prompt + contextual budget table snippets)
- **Average Output Tokens**: 300 tokens (structured budget comparison narrative, table excerpts, citations)

---

## 3. Projected Costs

### Scenario A: Primary Model (`gemini-1.5-pro`)

- **Cost per Question**:
  - Prompt: $500 \times \$0.00000350 = \$0.001750$
  - Completion: $300 \times \$0.00001050 = \$0.003150$
  - **Total per question**: **$0.004900** (~$0.0049)
- **Cost per 1,000 Questions**:
  - $1,000 \times \$0.004900 = \mathbf{\$4.90}$

### Scenario B: Fallback Model (`gemini-1.5-flash`)

- **Cost per Question**:
  - Prompt: $500 \times \$0.000000075 = \$0.0000375$
  - Completion: $300 \times \$0.00000030 = \$0.0000900$
  - **Total per question**: **$0.0001275** (~$0.00013)
- **Cost per 1,000 Questions**:
  - $1,000 \times \$0.0001275 = \mathbf{\$0.128}$ (approx. 13 cents)

---

## 4. Cost-Reduction Strategies

1. **Intelligent Model Routing (Flash-First / Pro-on-Demand)**:
   Route standard lookup queries (e.g., *"What was the BE for Defence in 2024?"*) to `gemini-1.5-flash` which is **38x cheaper**, and reserve `gemini-1.5-pro` strictly for complex cross-year variance diffing and deep anomaly analysis.
2. **Context Window Optimization & Chunk Trimming**:
   Pre-filter budget tables using metadata index filtering (demand number, ministry, year) before generating LLM prompts, keeping prompt size under 400 tokens rather than dumping entire page chapters.
3. **Response Caching**:
   Cache repeated identical historical budget questions in an in-memory or Redis key-value store. Budget actuals from prior fiscal years do not change once gazetted, resulting in 100% token savings for repeated analytical lookups.
