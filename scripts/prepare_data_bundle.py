import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def main() -> None:
    bundle_url = os.getenv("DATA_BUNDLE_URL", "").strip()
    if bundle_url:
        _download_and_extract(bundle_url, DATA_DIR / "_bundle.zip", DATA_DIR)

    zip_specs = [
        ("RAW_DATA_ZIP_URL", DATA_DIR / "_raw.zip"),
        ("PROCESSED_DATA_ZIP_URL", DATA_DIR / "_processed.zip"),
        ("INDEXES_DATA_ZIP_URL", DATA_DIR / "_indexes.zip"),
    ]
    for env_name, target in zip_specs:
        url = os.getenv(env_name, "").strip()
        if url:
            _download_and_extract(url, target, DATA_DIR)

    if not bundle_url and not any(os.getenv(name, "").strip() for name, _ in zip_specs):
        print("No data bundle URLs configured; continuing with local files or GitHub fallback.")


def _download_and_extract(url: str, target: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading data bundle from {url}")
    with urlopen(url, timeout=120) as response:
        target.write_bytes(response.read())
    with zipfile.ZipFile(target) as archive:
        archive.extractall(output_dir)
    target.unlink(missing_ok=True)
    print(f"Extracted {url} into {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Data bundle preparation failed: {exc}", file=sys.stderr)
        raise
