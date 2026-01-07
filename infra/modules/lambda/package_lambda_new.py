from __future__ import annotations

import hashlib
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


# Root directory of this script: lambda/functions/
SCRIPT_DIR = Path(__file__).resolve().parent / "functions"

# Exclusions (directories anywhere in the tree)
EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    ".venv",
    "venv",
    "node_modules",
}

# Exclusions (file suffixes)
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".DS_Store",
}

# Exclusions (exact file names)
EXCLUDE_FILE_NAMES = {
    ".env",
}


@dataclass(frozen=True)
class LambdaFunction:
    """
    Represents a Lambda function directory under:
      lambda/functions/<name>/

    Expected structure:
      lambda_function/handler.py
      package/ (output)
    """
    name: str
    root: Path
    source_dir: Path          # root/lambda_function
    package_dir: Path         # root/package
    output_zip: Path          # root/package/lambda.zip


class BuildError(RuntimeError):
    pass


def discover_functions(functions_dir: Path = SCRIPT_DIR) -> List[LambdaFunction]:
    """
    Discover lambda functions under lambda/functions/.

    A function is any directory containing a lambda_function/ subdirectory.
    """
    if not functions_dir.exists():
        raise FileNotFoundError(f"Functions directory not found: {functions_dir}")

    funcs: List[LambdaFunction] = []
    for child in sorted(p for p in functions_dir.iterdir() if p.is_dir()):
        source_dir = child / "lambda_function"
        if not source_dir.is_dir():
            continue

        name = child.name
        package_dir = child / "package"
        output_zip = package_dir / "lambda.zip"
        funcs.append(LambdaFunction(name=name, root=child, source_dir=source_dir, package_dir=package_dir, output_zip=output_zip))

    return funcs


def _should_exclude(path: Path) -> bool:
    # exclude by filename
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    # exclude by suffix
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    # exclude if any parent directory matches excluded names
    if any(parent.name in EXCLUDE_DIR_NAMES for parent in path.parents):
        return True
    return False


def _iter_files(source_dir: Path) -> List[Path]:
    files: List[Path] = []
    for p in source_dir.rglob("*"):
        if p.is_dir():
            continue
        if _should_exclude(p):
            continue
        files.append(p)
    return sorted(files)


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_size_kb_mb(path: Path) -> tuple[float, float]:
    size_bytes = path.stat().st_size
    size_kb = size_bytes / 1024
    size_mb = size_kb / 1024
    return size_kb, size_mb


def build_function(func: LambdaFunction, clean: bool = True) -> Path:
    """
    Build a single Lambda zip.

    Output:
      <func.root>/package/lambda.zip
    """
    # Basic validation
    if not func.source_dir.is_dir():
        raise BuildError(f"[{func.name}] Missing source dir: {func.source_dir}")

    handler_py = func.source_dir / "handler.py"
    if not handler_py.is_file():
        raise BuildError(f"[{func.name}] Missing handler.py in {func.source_dir}")

    func.package_dir.mkdir(parents=True, exist_ok=True)

    if clean and func.output_zip.exists():
        func.output_zip.unlink()

    files = _iter_files(func.source_dir)
    if not files:
        raise BuildError(f"[{func.name}] No files to package under {func.source_dir}")

    # Write to a temp zip then atomically replace the final file
    tmp_zip = func.package_dir / "lambda.zip.tmp"

    if tmp_zip.exists():
        tmp_zip.unlink()

    with zipfile.ZipFile(tmp_zip, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for abs_path in files:
            # IMPORTANT: zip paths relative to lambda_function/, so handler.py is at zip root
            arcname = abs_path.relative_to(func.source_dir).as_posix()
            zf.write(abs_path, arcname)

    # Atomic replace (best effort across platforms)
    tmp_zip.replace(func.output_zip)

    return func.output_zip


def build_all(functions_dir: Path = SCRIPT_DIR, clean: bool = True) -> List[Tuple[str, Path, str, float, float]]:
    """
    Build all discovered Lambda functions.

    Returns a list of (function_name, zip_path, sha256_prefix)
    """
    funcs = discover_functions(functions_dir)
    if not funcs:
        raise BuildError(f"No lambda functions found in: {functions_dir}")

    results: List[Tuple[str, Path, str, float, float]] = []
    errors: List[str] = []

    for func in funcs:
        try:
            zip_path = build_function(func, clean=clean)
            sha = _sha256_of_file(zip_path)[:12]
            size_kb, size_mb = _file_size_kb_mb(zip_path)
            results.append((func.name, zip_path, sha, size_kb, size_mb))

        except Exception as e:
            errors.append(f"[{func.name}] {e}")

    if errors:
        raise BuildError("Some builds failed:\n" + "\n".join(errors))

    return results


# Optional convenience entrypoint for "python build_lambda.py"
# (no CLI flags/args; it just builds everything)
def main() -> None:
    results = build_all(clean=True)
    for name, zip_path, sha, size_kb, size_mb in results:
        print(
            f"✅ {name}: {zip_path} | "
            f"size={size_kb:.1f} KB ({size_mb:.2f} MB) | "
            f"sha256={sha}..."
        )


if __name__ =="__main__":
    main()