from __future__ import annotations

import fnmatch
import hashlib
import logging
import platform
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

log = logging.getLogger("lambda_layer_builder")

# --------------------------------------------------------------------------------------
# Target for AWS Lambda Python 3.12 on x86_64
# --------------------------------------------------------------------------------------
TARGET_PLATFORM = "manylinux2014_x86_64"
TARGET_IMPLEMENTATION = "cp"
TARGET_PYTHON_VERSION = "312"
TARGET_ABI = "cp312"

# --------------------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------------------

DEFAULT_EXCLUDES: Tuple[str, ...] = (
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.dist-info/RECORD",
    "*.dist-info/WHEEL",
    "*.dist-info/top_level.txt",
    "*.dist-info/INSTALLER",
    "*.egg-info/",
    ".DS_Store",
)

DEFAULT_PRUNE_DIR_NAMES: Tuple[str, ...] = (
    "__pycache__",
    "tests",
    "test",
    "testing",
    "benchmarks",
    "benchmark",
    "docs",
    "doc",
    "examples",
    "example",
    ".pytest_cache",
)

DEFAULT_PRUNE_GLOBS: Tuple[str, ...] = (
    "*.pyc",
    "*.pyo",
    "*.dist-info/RECORD",
    "*.dist-info/WHEEL",
    "*.dist-info/top_level.txt",
    "*.dist-info/INSTALLER",
    "*.dist-info/entry_points.txt",
    "*.dist-info/direct_url.json",
    "*.egg-info/*",
    "*.a",
    "*.la",
    "*.so.debug",
)

DEFAULT_REMOVE_DIST_INFO: bool = True
DEFAULT_REMOVE_EGG_INFO: bool = True


@dataclass(frozen=True)
class LayerPaths:
    root: Path
    requirements_dir: Path
    outputs_dir: Path

    @staticmethod
    def from_repo_root(root: Path) -> "LayerPaths":
        return LayerPaths(
            root=root,
            requirements_dir=root / "layers" / "requirements",
            outputs_dir=root / "layers" / "outputs",
        )


@dataclass(frozen=True)
class BuildOptions:
    python_executable: Path
    python_version: str
    upgrade_pip: bool = True
    clean_output: bool = True

    excludes: Tuple[str, ...] = DEFAULT_EXCLUDES

    enable_prune: bool = True
    prune_dir_names: Tuple[str, ...] = DEFAULT_PRUNE_DIR_NAMES
    prune_globs: Tuple[str, ...] = DEFAULT_PRUNE_GLOBS
    remove_dist_info: bool = DEFAULT_REMOVE_DIST_INFO
    remove_egg_info: bool = DEFAULT_REMOVE_EGG_INFO

    enable_strip: bool = True
    strip_mode: str = "--strip-unneeded"

    force_lambda_target_wheels: bool = True


class LayerBuildError(RuntimeError):
    pass


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _run(cmd: Sequence[str], *, cwd: Optional[Path] = None) -> str:
    try:
        p = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd else None,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return p.stdout or ""
    except subprocess.CalledProcessError as e:
        out = e.stdout or ""
        raise LayerBuildError(f"Command failed: {' '.join(cmd)}\n{out[:4000]}") from e


def _python_version_of(python_exe: Path) -> str:
    out = subprocess.check_output(
        [str(python_exe), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        text=True,
    ).strip()
    if not out or "." not in out:
        raise LayerBuildError(f"Could not detect python version from {python_exe} (got {out!r})")
    return out


def _has_python_pip(python_exe: Path) -> bool:
    try:
        subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return True
    except Exception:
        return False


def _try_ensurepip(python_exe: Path) -> bool:
    try:
        subprocess.run(
            [str(python_exe), "-m", "ensurepip", "--upgrade"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return True
    except Exception:
        return False


def _resolve_pip_cmd(python_exe: Path) -> list[str]:
    if _has_python_pip(python_exe):
        return [str(python_exe), "-m", "pip"]

    log.warning("pip not found for %s. Trying ensurepip...", python_exe)
    if _try_ensurepip(python_exe) and _has_python_pip(python_exe):
        log.info("✅ pip bootstrapped via ensurepip for %s", python_exe)
        return [str(python_exe), "-m", "pip"]

    raise LayerBuildError(
        "pip is not available for the selected Python executable.\n\n"
        f"Python: {python_exe}\n"
        "Fix (WSL Ubuntu/Debian):\n"
        "  sudo apt-get update\n"
        "  sudo apt-get install -y python3.12-venv python3-pip\n\n"
        "Then verify:\n"
        "  python3.12 -m pip --version\n"
    )


def resolve_python(
    *,
    python_executable: Optional[Path] = None,
    python_version: Optional[str] = None,
) -> Tuple[Path, str]:
    if python_executable:
        exe = python_executable.expanduser().resolve()
        if not exe.exists():
            raise LayerBuildError(f"Python executable not found: {exe}")
        detected = _python_version_of(exe)
        if python_version and detected != python_version:
            raise LayerBuildError(f"Python mismatch: requested {python_version}, got {detected} at {exe}")
        return exe, detected

    if python_version:
        for name in (f"python{python_version}", f"python3.{python_version.split('.')[-1]}"):
            found = shutil.which(name)
            if found:
                exe = Path(found).resolve()
                detected = _python_version_of(exe)
                if detected == python_version:
                    return exe, detected
        raise LayerBuildError(
            f"Could not find a python executable for version {python_version}. Provide python_executable explicitly."
        )

    found = shutil.which("python") or shutil.which("python3")
    if not found:
        raise LayerBuildError("Could not resolve current python executable (python/python3 not found)")
    exe = Path(found).resolve()
    return exe, _python_version_of(exe)


def _matches_any(patterns: Iterable[str], rel_posix: str) -> bool:
    for pat in patterns:
        if pat.endswith("/"):
            if rel_posix.startswith(pat):
                return True
        else:
            if fnmatch.fnmatch(rel_posix, pat):
                return True
    return False


def _zip_dir(src_dir: Path, zip_path: Path, *, excludes: Tuple[str, ...]) -> None:
    fixed_date = (1980, 1, 1, 0, 0, 0)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted([x for x in src_dir.rglob("*") if x.is_file()]):
            rel = p.relative_to(src_dir).as_posix()
            if _matches_any(excludes, rel):
                continue
            data = p.read_bytes()
            info = zipfile.ZipInfo(filename=rel, date_time=fixed_date)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, data)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except FileNotFoundError:
                continue
    return total


def _human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    v = float(n)
    for u in units:
        if v < 1024.0 or u == units[-1]:
            return f"{v:.1f} {u}"
        v /= 1024.0
    return f"{v:.1f} B"


def _prune_site_packages(
    site_packages: Path,
    *,
    dir_names: Tuple[str, ...],
    globs: Tuple[str, ...],
    remove_dist_info: bool,
    remove_egg_info: bool,
) -> None:
    if not site_packages.exists():
        return

    before = _dir_size_bytes(site_packages)
    removed_dirs = 0
    removed_files = 0

    for name in dir_names:
        for d in site_packages.rglob(name):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
                removed_dirs += 1

    if remove_dist_info:
        for d in site_packages.glob("*.dist-info"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
                removed_dirs += 1

    if remove_egg_info:
        for d in site_packages.glob("*.egg-info"):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
                removed_dirs += 1

    for pat in globs:
        for p in site_packages.rglob(pat):
            if p.is_file():
                try:
                    p.unlink()
                    removed_files += 1
                except FileNotFoundError:
                    continue
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed_dirs += 1

    share_dir = site_packages / "share"
    if share_dir.exists() and share_dir.is_dir():
        shutil.rmtree(share_dir, ignore_errors=True)
        removed_dirs += 1

    after = _dir_size_bytes(site_packages)
    log.info(
        "🧹 Prune site-packages: removed_dirs=%d removed_files=%d size %s -> %s (saved %s)",
        removed_dirs,
        removed_files,
        _human_bytes(before),
        _human_bytes(after),
        _human_bytes(max(0, before - after)),
    )


def _find_strip() -> Optional[str]:
    if platform.system().lower() != "linux":
        return None
    for cand in ("strip", "llvm-strip"):
        p = shutil.which(cand)
        if p:
            return p
    return None


def _strip_shared_objects(site_packages: Path, *, mode: str) -> None:
    strip_bin = _find_strip()
    if not strip_bin:
        log.info("ℹ️  strip skipped (not Linux or strip not found).")
        return

    so_files = [p for p in site_packages.rglob("*.so") if p.is_file()]
    if not so_files:
        return

    before = sum(p.stat().st_size for p in so_files if p.exists())

    stripped = 0
    for so in so_files:
        try:
            subprocess.run([strip_bin, mode, str(so)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            stripped += 1
        except Exception:
            continue

    after = sum(p.stat().st_size for p in so_files if p.exists())
    log.info(
        "🪓 Stripped .so: files=%d stripped=%d size %s -> %s (saved %s)",
        len(so_files),
        stripped,
        _human_bytes(before),
        _human_bytes(after),
        _human_bytes(max(0, before - after)),
    )


def _assert_pyarrow_cp312(site_packages: Path) -> None:
    pyarrow_dir = site_packages / "pyarrow"
    if not pyarrow_dir.exists():
        return

    so_files = list(pyarrow_dir.glob("lib.*.so"))
    names = [p.name for p in so_files]
    log.info("🔎 pyarrow native libs: %s", names[:6])

    if not so_files:
        raise LayerBuildError("pyarrow is present but no native lib.*.so was found under pyarrow/")

    ok = any(("cpython-312" in n) or ("cp312" in n) for n in names)
    if not ok:
        raise LayerBuildError(
            "pyarrow native extension is not cp312. This layer will NOT work on Lambda Python 3.12.\n"
            f"Found: {names[:6]}\n"
        )


def _assert_numpy_not_source_tree(site_packages: Path) -> None:
    """
    If numpy is installed from a wheel, it contains compiled extensions.
    If it looks like the numpy source tree, importing will fail with:
      'you should not try to import numpy from its source directory'
    """
    numpy_dir = site_packages / "numpy"
    if not numpy_dir.exists():
        return

    # Strong signal for source tree:
    if (numpy_dir / "setup.py").exists() or (numpy_dir / "tools").exists():
        raise LayerBuildError(
            "NumPy in site-packages looks like a source tree (numpy/setup.py or numpy/tools found).\n"
            "This will fail on Lambda. Ensure you install NumPy from a manylinux cp312 wheel.\n"
        )

    # Strong signal for a valid wheel: compiled core extension
    core_so = list(numpy_dir.rglob("_multiarray_umath*.so"))
    if not core_so:
        raise LayerBuildError(
            "NumPy appears installed without compiled core extension (_multiarray_umath*.so not found).\n"
            "This usually means you did not get a compatible wheel.\n"
        )


def _install_lambda_target_wheels(
    pip_cmd: Sequence[str],
    requirements_file: Path,
    site_packages: Path,
    wheels_dir: Path,
) -> None:
    wheels_dir.mkdir(parents=True, exist_ok=True)

    log.info("⬇️  Downloading wheels for %s / %s ...", TARGET_PLATFORM, TARGET_ABI)
    _run([
        *pip_cmd, "download",
        "--no-cache-dir",
        "--only-binary=:all:",
        "--platform", TARGET_PLATFORM,
        "--implementation", TARGET_IMPLEMENTATION,
        "--python-version", TARGET_PYTHON_VERSION,
        "--abi", TARGET_ABI,
        "--dest", str(wheels_dir),
        "-r", str(requirements_file),
    ])

    log.info("📥 Installing from downloaded wheels (no-index) ...")
    _run([
        *pip_cmd, "install",
        "--no-cache-dir",
        "--no-index",
        "--find-links", str(wheels_dir),
        "--only-binary=:all:",
        "--target", str(site_packages),
        "-r", str(requirements_file),
        "--no-compile",
    ])


def build_layer(
    *,
    paths: LayerPaths,
    layer_name: str,
    requirements_file: Path,
    options: BuildOptions,
) -> Path:
    if not requirements_file.exists():
        raise LayerBuildError(f"Requirements file not found: {requirements_file}")

    paths.outputs_dir.mkdir(parents=True, exist_ok=True)
    out_zip = paths.outputs_dir / f"{layer_name}.zip"

    if options.clean_output and out_zip.exists():
        out_zip.unlink()

    detected = _python_version_of(options.python_executable)
    if detected != options.python_version:
        raise LayerBuildError(
            f"BuildOptions python_version={options.python_version} "
            f"doesn't match detected version {detected} from {options.python_executable}"
        )

    log.info("🐍 Python executable: %s", options.python_executable)
    log.info("🐍 Python version used for build: %s", detected)
    log.info("📦 Building layer '%s' (python %s)", layer_name, options.python_version)
    log.info("   Requirements: %s", requirements_file)

    with tempfile.TemporaryDirectory(prefix=f"layer-{layer_name}-") as tmpdir:
        tmp = Path(tmpdir)
        root = tmp / "layer_root"
        site_packages = root / "python" / "lib" / f"python{options.python_version}" / "site-packages"
        site_packages.mkdir(parents=True, exist_ok=True)

        pip_cmd = _resolve_pip_cmd(options.python_executable)

        if options.upgrade_pip:
            _run([*pip_cmd, "install", "--upgrade", "pip", "setuptools", "wheel"])

        if options.force_lambda_target_wheels:
            wheels_dir = tmp / "wheels"
            _install_lambda_target_wheels(pip_cmd, requirements_file, site_packages, wheels_dir)
        else:
            _run([
                *pip_cmd, "install",
                "-r", str(requirements_file),
                "--target", str(site_packages),
                "--no-compile",
                "--no-cache-dir",
            ])

        # Guardrails for native deps
        _assert_numpy_not_source_tree(site_packages)
        _assert_pyarrow_cp312(site_packages)

        if options.enable_prune:
            log.info("📦 site-packages size before prune: %s", _human_bytes(_dir_size_bytes(site_packages)))
            _prune_site_packages(
                site_packages,
                dir_names=options.prune_dir_names,
                globs=options.prune_globs,
                remove_dist_info=options.remove_dist_info,
                remove_egg_info=options.remove_egg_info,
            )

        if options.enable_strip:
            _strip_shared_objects(site_packages, mode=options.strip_mode)

        _zip_dir(root, out_zip, excludes=options.excludes)

    log.info(
        "✅ Created %s (size=%.1f KB, sha256=%s)",
        out_zip.name,
        out_zip.stat().st_size / 1024,
        _sha256_file(out_zip),
    )
    return out_zip


def build_all_layers(
    *,
    repo_root: Optional[Path] = None,
    python_executable: Optional[Path] = None,
    python_version: Optional[str] = None,
    upgrade_pip: bool = True,
    clean_output: bool = True,
    excludes: Tuple[str, ...] = DEFAULT_EXCLUDES,
    enable_prune: bool = True,
    remove_dist_info: bool = DEFAULT_REMOVE_DIST_INFO,
    remove_egg_info: bool = DEFAULT_REMOVE_EGG_INFO,
    enable_strip: bool = True,
    strip_mode: str = "--strip-unneeded",
    force_lambda_target_wheels: bool = True,
) -> list[Path]:
    root = (repo_root or Path(__file__).resolve().parent).resolve()
    paths = LayerPaths.from_repo_root(root)

    if not paths.requirements_dir.exists():
        raise LayerBuildError(f"Requirements directory not found: {paths.requirements_dir}")

    exe, ver = resolve_python(python_executable=python_executable, python_version=python_version)

    opts = BuildOptions(
        python_executable=exe,
        python_version=ver,
        upgrade_pip=upgrade_pip,
        clean_output=clean_output,
        excludes=excludes,
        enable_prune=enable_prune,
        remove_dist_info=remove_dist_info,
        remove_egg_info=remove_egg_info,
        enable_strip=enable_strip,
        strip_mode=strip_mode,
        force_lambda_target_wheels=force_lambda_target_wheels,
    )

    paths.outputs_dir.mkdir(parents=True, exist_ok=True)

    built: list[Path] = []
    req_files = sorted(paths.requirements_dir.glob("*.txt"))
    if not req_files:
        log.warning("No requirements files found in %s", paths.requirements_dir)
        return built

    log.info("🚀 Starting layers build (%d requirements files)", len(req_files))
    for req in req_files:
        name = req.stem
        built.append(build_layer(paths=paths, layer_name=name, requirements_file=req, options=opts))

    log.info("🎉 All layers built: %d", len(built))
    return built


if __name__ == "__main__":
    setup_logging(logging.INFO)

    build_all_layers(
        repo_root=Path(__file__).parent,
        python_version="3.12",
        enable_prune=True,
        remove_dist_info=True,
        remove_egg_info=True,
        enable_strip=True,
        strip_mode="--strip-unneeded",
        force_lambda_target_wheels=True,
    )
