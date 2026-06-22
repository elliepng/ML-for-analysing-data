"""Tao goi phan phoi Windows x64 cho Fraud Detection Dashboard.

Chay tu thu muc goc du an:
    python scripts/make_package.py

Ket qua: dist/fraud-detection-win64.zip (~15 MB)

Goi bao gom:
  - Source code (app/, scripts/, tests/)
  - artifacts/*.pkl, *.json, *.csv  (mo hinh + ket qua da chay)
  - requirements.txt (version pin cung)
  - run_windows.bat, README.md

Khong bao gom:
  - .venv/  (nguoi dung tu cai qua run_windows.bat)
  - artifacts/*.parquet (360 MB - qua lon)
  - data/raw/*.csv  (du lieu goc, qua lon)
  - .git/, __pycache__, .DS_Store
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist"

INCLUDE_TOP = [
    "app",
    "scripts",
    "tests",
]

INCLUDE_FILES = [
    "requirements.txt",
    "run_windows.bat",
    "README.md",
    "CLAUDE.md",
    "KARPATHY.md",
]

ARTIFACT_EXTENSIONS = {".pkl", ".json", ".csv"}

EXCLUDE_NAMES = {".DS_Store", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv", ".git", "dist"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_NAMES for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def add_directory(zf: zipfile.ZipFile, directory: Path, base: Path) -> int:
    count = 0
    for file in sorted(directory.rglob("*")):
        if not file.is_file():
            continue
        if not should_include(file):
            continue
        zf.write(file, file.relative_to(base))
        count += 1
    return count


def main() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    output = DIST_DIR / "fraud-detection-win64.zip"
    output.unlink(missing_ok=True)

    total = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name in INCLUDE_FILES:
            path = ROOT / name
            if path.exists():
                zf.write(path, name)
                total += 1

        for top in INCLUDE_TOP:
            total += add_directory(zf, ROOT / top, ROOT)

        artifacts_dir = ROOT / "artifacts"
        if artifacts_dir.exists():
            for file in sorted(artifacts_dir.iterdir()):
                if file.is_file() and file.suffix in ARTIFACT_EXTENSIONS:
                    zf.write(file, file.relative_to(ROOT))
                    size_mb = file.stat().st_size / 1_048_576
                    print(f"  + artifacts/{file.name}  ({size_mb:.1f} MB)")
                    total += 1

    size_mb = output.stat().st_size / 1_048_576
    print(f"\nTao thanh cong: {output.relative_to(ROOT)}  ({size_mb:.1f} MB, {total} files)")
    print("\nHuong dan chuyen sang Windows:")
    print("  1. Sao chep dist/fraud-detection-win64.zip sang may Windows")
    print("  2. Giai nen vao thu muc bat ky")
    print("  3. Cai Python 3.11 hoac 3.12 (x64) tu python.org neu chua co")
    print("  4. Nhan doi chuot vao run_windows.bat")
    print("     - Lan dau: tu dong cai thu vien (~2-5 phut, can Internet)")
    print("     - Browser tu mo tai http://localhost:8501")


if __name__ == "__main__":
    main()
