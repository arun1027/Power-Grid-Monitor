import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(r"d:\Power Grid Monitor")
OUT = ROOT / "eb_deploy_package.zip"
EXCLUDE_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__", ".platform"}

if OUT.exists():
    OUT.unlink()

if (ROOT / ".ebextensions").exists():
    shutil.rmtree(ROOT / ".ebextensions")

files = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    if any(part in EXCLUDE_DIRS for part in path.parts):
        continue
    if path == OUT:
        continue
    rel = path.relative_to(ROOT).as_posix()
    files.append((path, rel))

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path, rel in sorted(files):
        zf.write(path, rel)

print(f"Created {OUT}")
print(f"Entries: {len(files)}")
print("Sample entries:")
for _, rel in sorted(files)[:10]:
    print(rel)
