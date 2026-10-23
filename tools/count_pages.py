import sys
from pathlib import Path

from pypdf import PdfReader


def count_pages(target_dir: str = "data/raw") -> int:
    """Scan directory for PDF documents and count total pages programmatically."""
    target_path = Path(target_dir)
    if not target_path.exists():
        print(f"Directory not found: {target_dir}")
        return 0

    total_pages = 0
    total_files = 0
    print(f"Scanning '{target_dir}' for PDF documents...\n")
    print(f"{'Filename':<35} {'Pages':>8} {'Size (KB)':>12}")
    print("-" * 58)

    pdf_files = sorted(target_path.rglob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {target_dir}.")
        return 0

    for file_path in pdf_files:
        try:
            reader = PdfReader(str(file_path))
            num_pages = len(reader.pages)
            size_kb = file_path.stat().st_size / 1024
            total_pages += num_pages
            total_files += 1
            print(f"{file_path.name:<35} {num_pages:>8} {size_kb:>11.1f} KB")
        except Exception as e:
            print(f"{file_path.name:<35} Error reading PDF: {e}")

    print("-" * 58)
    print(f"Total: {total_files} files, {total_pages} pages")
    return total_pages


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
    count_pages(path)
