"""Build the importable plugin: dist/opendeck-uno-overlays-<version>-linux.plugin.zip

Before packaging it checks what a release must never get wrong:
- the vendored websockets files are byte-identical to the pinned official wheel (supply chain);
- manifest.json, uno/__init__.py and pyproject.toml carry the same version;
- no cache or editor file is inside the plugin folder.
Then it rewrites the plugin's SHA256SUMS and writes a reproducible ZIP (sorted entries, fixed
timestamps from SOURCE_DATE_EPOCH or the CHANGELOG release date, fixed permissions), plus the same
files expanded in dist/expanded/, where CI runs launch.sh --version and checks SHA256SUMS.

    python3 -B scripts/build.py
"""

import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import sys
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
WHEEL = ROOT / "third_party" / "websockets-15.0.1-py3-none-any.whl"
WHEEL_SHA256 = "f7a866fbc1e97b5c617ee4116daaa09b722101d4a3c170c787450ba409f9736f"  # PyPI, websockets 15.0.1
EXECUTABLE = {"launch.sh"}
JUNK = re.compile(r"(^|/)(__pycache__|\.ruff_cache|\.mypy_cache|\.pytest_cache)(/|$)|\.pyc$|~$|\.swp$|\.DS_Store$")


def fail(message):
    sys.exit(f"build: {message}")


def check_vendor():
    if hashlib.sha256(WHEEL.read_bytes()).hexdigest() != WHEEL_SHA256:
        fail(f"{WHEEL.name} does not match the pinned SHA-256")
    vendor = PLUGIN / "vendor"
    with zipfile.ZipFile(WHEEL) as wheel:
        names = {n for n in wheel.namelist() if n.startswith("websockets/")}
        changed = sorted(n for n in names if not (vendor / n).is_file() or (vendor / n).read_bytes() != wheel.read(n))
        license_ok = wheel.read("websockets-15.0.1.dist-info/LICENSE") == (vendor / "websockets-LICENSE").read_bytes()
    extra = sorted(str(p.relative_to(vendor)) for p in (vendor / "websockets").rglob("*") if p.is_file())
    extra = [n for n in extra if n not in names]
    if changed or extra or not license_ok:
        fail(f"vendor/websockets differs from the official wheel: {changed + extra or 'LICENSE'}")


def check_version():
    manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))["Version"]
    package = re.search(r'VERSION = "([^"]+)"', (PLUGIN / "uno" / "__init__.py").read_text(encoding="utf-8"))[1]
    project = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)[1]
    if not manifest == package == project:
        fail(f"versions differ: manifest {manifest}, uno {package}, pyproject {project}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", manifest):
        fail("OpenDeck reads the manifest Version as semver: use MAJOR.MINOR.PATCH")
    return manifest


def release_time():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:  # reproducible-builds.org: seconds since 1970-01-01 UTC, as `date +%s` prints
        if not epoch.isdigit():
            fail("SOURCE_DATE_EPOCH must be an integer number of seconds")
        return max(time.gmtime(int(epoch))[:6], (1980, 1, 1, 0, 0, 0))  # ZIP dates start in 1980
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    date = re.search(r"^## \[\d+\.\d+\.\d+\] [-–—] (\d{4})-(\d{2})-(\d{2})", changelog, re.M)
    if not date:
        fail("CHANGELOG.md has no released version (## [x.y.z] - YYYY-MM-DD)")
    return tuple(int(x) for x in date.groups()) + (0, 0, 0)


def plugin_files():
    files = sorted(p.relative_to(PLUGIN).as_posix() for p in PLUGIN.rglob("*") if p.is_file())
    junk = [f for f in files if JUNK.search(f)]
    if junk:
        fail(f"remove these from the plugin folder first: {junk}")
    return [f for f in files if f != "SHA256SUMS"]


def main():
    check_vendor()
    version = check_version()
    files = plugin_files()
    sums = "".join(f"{hashlib.sha256((PLUGIN / f).read_bytes()).hexdigest()}  {f}\n" for f in files)
    (PLUGIN / "SHA256SUMS").write_text(sums, encoding="utf-8")
    stamp = release_time()
    out = ROOT / "dist" / f"opendeck-uno-overlays-{version}-linux.plugin.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w") as archive:
        for name in sorted(files + ["SHA256SUMS"]):
            info = zipfile.ZipInfo(f"{PLUGIN.name}/{name}", stamp)
            info.external_attr = (stat.S_IFREG | (0o755 if name in EXECUTABLE else 0o644)) << 16  # regular file + mode
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (PLUGIN / name).read_bytes(), compresslevel=9)  # ZipInfo ignores the ZipFile's
    expanded = ROOT / "dist" / "expanded"
    shutil.rmtree(expanded, ignore_errors=True)
    for name in files + ["SHA256SUMS"]:
        target = expanded / PLUGIN.name / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PLUGIN / name, target)
        target.chmod(0o755 if name in EXECUTABLE else 0o644)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out.relative_to(ROOT)}  {len(files) + 1} files  sha256 {digest}")


if __name__ == "__main__":
    main()
