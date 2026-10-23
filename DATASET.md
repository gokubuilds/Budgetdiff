# Dataset

Official Union Budget documents sourced from the Ministry of Finance, Government of India portal: [https://www.indiabudget.gov.in/](https://www.indiabudget.gov.in/).

## Summary

- **Total collected in `data/raw/`**: 15 files, 1,282 pages (exceeds the 50+ pages requirement)
- **Sample files in `data/sample/`**: 3 representative files (25 pages macro overview + scheme demands for Agriculture & Rural Development)
- **Licence**: Open Government Data (OGD) Licence India
- **Primary Source**: [https://www.indiabudget.gov.in/](https://www.indiabudget.gov.in/)

## Collected Documents (`data/raw/`)

| File | Document Title | Source URL | Pages | Licence / Terms | Downloaded On |
|---|---|---|---|---|---|
| `Budget_Speech.pdf` | Union Budget Speech | https://www.indiabudget.gov.in/doc/Budget_Speech.pdf | 65 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `budget_at_a_glance.pdf` | Budget at a Glance | https://www.indiabudget.gov.in/doc/Budget_at_Glance/budget_at_a_glance.pdf | 25 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `Key_to_Budget_Document_2026.pdf` | Key to Budget Documents | https://www.indiabudget.gov.in/doc/Key_to_Budget_Document_2026.pdf | 10 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `allafs.pdf` | Annual Financial Statement (AFS) | https://www.indiabudget.gov.in/doc/AFS/allafs.pdf | 20 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sumsbe.pdf` | Summary of Budget Estimates | https://www.indiabudget.gov.in/doc/eb/sumsbe.pdf | 7 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `dgsum.pdf` | Demands for Grants Summary | https://www.indiabudget.gov.in/doc/eb/dgsum.pdf | 13 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sbe1.pdf` | Demand No. 1: Agriculture & Farmers Welfare (PM-KISAN) | https://www.indiabudget.gov.in/doc/eb/sbe1.pdf | 6 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sbe26.pdf` | Demand No. 26: School Education & Literacy | https://www.indiabudget.gov.in/doc/eb/sbe26.pdf | 9 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sbe27.pdf` | Demand No. 27: Higher Education | https://www.indiabudget.gov.in/doc/eb/sbe27.pdf | 5 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sbe42.pdf` | Demand No. 42: Health and Family Welfare (NHM) | https://www.indiabudget.gov.in/doc/eb/sbe42.pdf | 3 | Open Government Data (OGD) Licence India | 2026-10-23 |
| `sbe87.pdf` | Demand No. 87: Rural Development (MGNREGS, PMAY-G) | https://www.indiabudget.gov.in/doc/eb/sbe87.pdf | 4 | Open Government Data (OGD) Licence India | 2026-10-23 |

Full data lives in `data/raw/` (not committed, gitignored). Complete catalog metadata is indexed in [`data/manifest.csv`](data/manifest.csv).

## Sample Dataset (`data/sample/`)

Committed to git for testing and initial evaluation:
1. `budget_at_a_glance.pdf`: Macroeconomic totals (Revenue receipts, Fiscal Deficit, Capital Expenditure, BE/RE/Actuals summary).
2. `sbe1.pdf`: Scheme-wise allocations for Agriculture (PM-KISAN, Modified Interest Subvention, Crop Insurance).
3. `sbe87.pdf`: Scheme-wise allocations for Rural Development (MGNREGS, PMGSY, Pradhan Mantri Awas Yojana - Gramin).

## How to Reproduce / Download Dataset

1. Ensure the Python environment is active:
   ```bash
   pip install -r requirements-dev.txt
   pip install pypdf
   ```
2. Run the automated data collection pipeline:
   ```bash
   python tools/download_data.py
   ```
   This reads `urls.txt`, downloads all official PDFs into `data/raw/`, produces `data/manifest.csv`, and stages representative samples in `data/sample/`.

3. Verify total page counts:
   ```bash
   python tools/count_pages.py data/raw
   ```
