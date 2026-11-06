"""Build a portable Windows preview, licenses, SHA256 manifest, and startup report."""

from importlib import metadata
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "dv365-music-downloader"
VERSION = "0.1.0-preview"
PACKAGES = ("click", "requests", "certifi", "charset-normalizer", "idna", "urllib3",
            "pycryptodome", "prettytable", "wcwidth", "setuptools", "pyinstaller")


def notices(bundle):
    text = ["dv365-music-downloader 0.1.0-preview — Third-party notices",
            "技术预发布版。保留原项目授权文件；商业授权冲突尚待核实。",
            (ROOT / "LICENSE").read_text(encoding="utf-8")]
    inventory = []
    for name in PACKAGES:
        package = metadata.distribution(name)
        inventory.append({"name": name, "version": package.version})
        text.append("\n" + "=" * 72 + "\n" + name + " " + package.version)
        license_files = [item for item in package.files or []
                         if any(word in item.name.lower() for word in ("license", "copying", "notice"))
                         and (".dist-info" in str(item) or "pycryptodome" in str(item))]
        if not license_files:
            raise RuntimeError("Cannot locate redistribution license for " + name)
        for item in license_files:
            text.append(package.locate_file(item).read_text(encoding="utf-8", errors="replace"))
    # Python redistributions include Tcl/Tk and bundled runtime license notices.
    runtime = Path(sys.base_prefix)
    python_license = runtime / "LICENSE.txt"
    if not python_license.exists():
        raise RuntimeError("Python license not found")
    text.extend(["\n" + "=" * 72 + "\nPython " + sys.version, python_license.read_text(encoding="utf-8")])
    for directory, title in (("tcl8.6", "Tcl"), ("tk8.6", "Tk")):
        candidates = [runtime / "tcl" / directory / "license.terms",
                      bundle / "_internal" / ("_tcl_data" if title == "Tcl" else "_tk_data") / "license.terms"]
        found = next((item for item in candidates if item.exists()), None)
        if found:
            text.extend(["\n" + "=" * 72 + "\n" + title, found.read_text(encoding="utf-8", errors="replace")])
        elif title == "Tcl":
            # This Windows runtime distributes the Tcl license inside Python's LICENSE.txt.
            if "Tcl" not in python_license.read_text(encoding="utf-8"):
                raise RuntimeError("Tcl license not found in runtime notices")
    for notice in sorted((ROOT / "tools" / "licenses").glob("*.txt")):
        text.extend(["\n" + "=" * 72 + "\n" + notice.name, notice.read_text(encoding="utf-8")])
    (bundle / "THIRD_PARTY_NOTICES.txt").write_text("\n\n".join(text), encoding="utf-8")
    (bundle / "DEPENDENCIES.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")


def main():
    if sys.platform != "win32":
        raise RuntimeError("The Windows bundle must be built on Windows")
    if sys.version_info[:2] != (3, 11) or struct.calcsize("P") != 8:
        raise RuntimeError("Use the tested Python 3.11 x64 runtime for this preview")
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", NAME, "--icon", "NONE",
                    "--collect-submodules", "music_dl.addons", "--exclude-module", "pygame",
                    "--exclude-module", "PIL", "--exclude-module", "pytest",
                    "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"),
                    "--specpath", str(ROOT / "build"), str(ROOT / "desktop_entry.py")], cwd=ROOT, check=True)
    bundle = ROOT / "dist" / NAME
    for source, target in (("start.bat", "start.bat"), ("LICENSE", "LICENSE"), ("README.md", "ORIGINAL_README.md"),
                           ("DESKTOP_PREVIEW.md", "使用说明.md"), ("COMMERCIAL_REVIEW.md", "授权与接口核对.md")):
        shutil.copyfile(ROOT / source, bundle / target)
    notices(bundle)
    report = ROOT / "build" / "frozen-startup.json"
    if report.exists():
        report.unlink()
    subprocess.run([str(bundle / (NAME + ".exe")), "--smoke-test", str(report)], cwd=bundle, check=True, timeout=45)
    result = json.loads(report.read_text(encoding="utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Frozen startup failed: " + str(result))
    shutil.copyfile(report, bundle / "STARTUP_CHECK.json")
    manifest = []
    for file in sorted(bundle.rglob("*")):
        if file.is_file():
            manifest.append(hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.relative_to(bundle).as_posix())
    (bundle / "SHA256SUMS.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    archive = ROOT / "dist" / (NAME + "-" + VERSION + "-windows-x64.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        for file in bundle.rglob("*"):
            if file.is_file():
                output.write(file, file.relative_to(bundle.parent))
    print("BUNDLE:", bundle)
    print("ZIP:", archive)
    archive.with_suffix(".zip.sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="utf-8")
    print("STARTUP:", result)


if __name__ == "__main__":
    main()
