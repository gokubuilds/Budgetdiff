import csv
import io
from pathlib import Path
import shutil
import urllib.request
from datetime import UTC, datetime

from pypdf import PdfReader

# Document metadata definitions
DOC_METADATA = {
    "Budget_Speech.pdf": {
        "title": "Union Budget Speech",
        "description": (
            "Full text of Budget Speech outlining policy goals and priority allocations."
        ),
    },
    "budget_at_a_glance.pdf": {
        "title": "Budget at a Glance",
        "description": (
            "Macroeconomic overview of revenue, fiscal deficit, and summary of BE, RE, and Actuals."
        ),
    },
    "Key_to_Budget_Document_2026.pdf": {
        "title": "Key to Budget Documents",
        "description": (
            "Official explanatory guide detailing the role and structure of each Union Budget document."
        ),
    },
    "allafs.pdf": {
        "title": "Annual Financial Statement (AFS)",
        "description": (
            "Article 112 statement detailing estimated receipts and expenditures of the Government of India."
        ),
    },
    "sumsbe.pdf": {
        "title": "Summary of Budget Estimates (Demands for Grants)",
        "description": (
            "Consolidated summary table of Budget Estimates and Revised Estimates across all Ministries."
        ),
    },
    "dgsum.pdf": {
        "title": "Demands for Grants Summary",
        "description": "Summary statement of Demands for Grants submitted to Parliament.",
    },
    "sbe1.pdf": {
        "title": "Demand No. 1: Department of Agriculture and Farmers Welfare",
        "description": (
            "Detailed scheme-level allocations including PM-KISAN, Interest Subvention, and PMFBY."
        ),
    },
    "sbe26.pdf": {
        "title": "Demand No. 26: Department of School Education and Literacy",
        "description": "Detailed scheme-level allocations including Samagra Shiksha and PM POSHAN.",
    },
    "sbe27.pdf": {
        "title": "Demand No. 27: Department of Higher Education",
        "description": "Detailed allocations for Central Universities, IITs, NITs, and UGC scholarships.",
    },
    "sbe42.pdf": {
        "title": "Demand No. 42: Department of Health and Family Welfare",
        "description": "Detailed scheme allocations including National Health Mission (NHM) and PM-ABHIM.",
    },
    "sbe87.pdf": {
        "title": "Demand No. 87: Department of Rural Development",
        "description": "Detailed scheme-level allocations including MGNREGS, PMGSY, and PMAY-Gramin.",
    },
}

SAMPLE_FILES = [
    "budget_at_a_glance.pdf",
    "sbe1.pdf",
    "sbe87.pdf",
]


def download_dataset(
    urls_file: str = "urls.txt",
    raw_dir: str = "data/raw",
    sample_dir: str = "data/sample",
    manifest_path: str = "data/manifest.csv",
):
    base_path = Path(__file__).resolve().parent.parent
    raw_path = base_path / raw_dir
    sample_path = base_path / sample_dir
    manifest_file = base_path / manifest_path
    urls_path = base_path / urls_file

    raw_path.mkdir(parents=True, exist_ok=True)
    sample_path.mkdir(parents=True, exist_ok=True)

    with open(urls_path, encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    manifest_rows = []

    print(f"Downloading {len(urls)} documents to {raw_path}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for url in urls:
        filename = url.rstrip("/").split("/")[-1]
        dest_file = raw_path / filename

        print(f"Fetching {filename} from {url}...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()

        with open(dest_file, "wb") as out_f:
            out_f.write(data)

        # Count pages
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = len(reader.pages)
        except Exception:
            pages = 1

        meta = DOC_METADATA.get(
            filename,
            {
                "title": filename,
                "description": "Official Union Budget Document",
            },
        )

        manifest_rows.append(
            {
                "file_name": filename,
                "source_url": url,
                "document_title": meta["title"],
                "description": meta["description"],
                "pages": pages,
                "size_bytes": len(data),
                "licence": "Open Government Data (OGD) Licence India",
                "downloaded_on": today,
            }
        )

    # Write manifest.csv
    with open(manifest_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "file_name",
            "source_url",
            "document_title",
            "description",
            "pages",
            "size_bytes",
            "licence",
            "downloaded_on",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in manifest_rows:
            writer.writerow(row)

    print(f"\nManifest successfully written to {manifest_file} with {len(manifest_rows)} entries.")

    # Populate data/sample with 2-3 representative files
    for sample_file in SAMPLE_FILES:
        src = raw_path / sample_file
        dst = sample_path / sample_file
        if src.exists():
            shutil.copy2(src, dst)
            print(f"Copied sample file: {sample_file} -> {sample_dir}/")

    print("\nData collection finished successfully.")


if __name__ == "__main__":
    download_dataset()
