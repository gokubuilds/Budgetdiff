# BudgetDiff

> Know exactly what changed between Union Budget estimates, revised figures and actuals, year by year.

## Problem
Every scheme has a Budget Estimate, a Revised Estimate the next year and Actuals two years later, spread across Expenditure Budget and Demand for Grants documents. Researchers often quote an old estimate as if it were final, and finding 'what changed' between the interim and full budget takes days. BudgetDiff tracks every figure across all budget stages, enabling instant diffing between versions and ensuring policy researchers always work with the latest, verified figures.

## Who it is for
Policy researcher at a Chennai public-policy think tank who tracks central spending on education, health and rural schemes.

## Signature feature
Version timeline per scheme: one click shows BE, RE and Actual for every year with arrows marking cuts and increases.

## Hardest problem (my interview story)
Versioning: latest valid version. Each figure is stored with its budget year and its version (BE, RE, Actual, Interim). The retriever answers with the latest valid version by default, and BudgetDiff builds a 'diff' that lists every head whose allocation changed between two versions, with both citations.

## Dataset
| Source | Link | Documents | Pages | Licence / terms |
|---|---|---|---|---|
| Union Budget | https://www.indiabudget.gov.in/ | Budget at a Glance, Expenditure Profile, Demands for Grants, Receipt Budget, Finance Bill, Budget Speech (5+ years, including published Excel files) | 8,000+ (5+ budget years) | Open Government Data (OGD) Licence India |

## AI Agent (Weeks 7–12)
Natural-language data analyst (safe SQL). Budget tables are loaded into Postgres (ministry, scheme, year, version, amount). The agent turns questions like *"Which ministries saw RE below BE for three years in a row?"* into read-only SQL, explains the result, and calls BudgetDiff to fetch the page citations for each row.

## Target Metric
Version correctness: 95%+ of answers on a 60-question test set quote the correct version (BE/RE/Actual) and year.

## 10 real questions
See [docs/QUESTIONS.md](docs/QUESTIONS.md).

### Try these questions:
1. What was the Budget Estimate and Revised Estimate for PM-KISAN in 2025-26?
2. What changed in the Ministry of Education allocation between the interim and full budget of 2024-25?
3. Which five schemes had the largest gap between Revised Estimate and Actuals last year?

## Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # Windows: copy .env.example .env
uvicorn app.main:app --reload
curl localhost:8000/health
```

## Live link
<Added in Week 2>

