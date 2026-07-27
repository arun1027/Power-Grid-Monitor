import os
import shutil
import zipfile
from pathlib import Path

root = Path(r"d:\Power Grid Monitor")
out = root / "eb_deploy_package.zip"
exclude_dirs = {'.git', '.venv', '.pytest_cache', '__pycache__', '.platform', '.ebextensions'}
exclude_files = {'build_eb_zip.py', 'make_zip.py'}

if out.exists():
    out.unlink()

files = []
for path in root.rglob('*'):
    if not path.is_file():
        continue
    if any(part in exclude_dirs for part in path.parts):
        continue
    if path.name in exclude_files:
        continue
    if path == out:
        continue
    rel = path.relative_to(root).as_posix()
    files.append((path, rel))

with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    for path, rel in sorted(files):
        zf.write(path, rel)

print('created', out)
print('entries', len(files))
