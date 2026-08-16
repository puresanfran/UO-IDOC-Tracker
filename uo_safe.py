"""
uo_safe.py — Source file protection for UO Housing Analyzer
=============================================================
This module ensures the original UO game files are NEVER modified.

Rules enforced:
  1. All UO source files are opened READ-ONLY ("rb") only.
  2. On first run, SHA-256 checksums of all source files are recorded.
  3. On every subsequent run, checksums are verified — any change is a hard error.
  4. No file is ever written inside the UO source directory.
  5. All output goes exclusively to E:\\Ultima House Mapping\\

If a checksum mismatch is detected, the script stops immediately and
tells you exactly which file changed and by how much.
"""

import os
import sys
import json
import hashlib
import time

UO_PATH      = r"E:\Ultima Online"
PROJECT_PATH = r"E:\Ultima House Mapping"
OUTPUT_PATH  = os.path.join(PROJECT_PATH, "output")
CHECKSUM_FILE = os.path.join(PROJECT_PATH, "source_checksums.json")

# Files we read from the UO install
SOURCE_FILES = [
    "map0.mul",
    "staidx0.mul",
    "statics0.mul",
    "tiledata.mul",
    "radarcol.mul",
    "multi.mul",
    "multi.idx",
]


def _sha256(path, chunk=1024*1024):
    """Compute SHA-256 of a file without loading it all into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as f:       # READ-ONLY — never "w", "wb", "a", "r+"
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _file_info(path):
    st = os.stat(path)
    return {
        "size":     st.st_size,
        "mtime":    st.st_mtime,
        "sha256":   _sha256(path),
    }


def verify_source_integrity(verbose=True):
    """
    Called at the top of every script run.

    First run  → records checksums to source_checksums.json (in project folder, NOT in UO folder)
    Later runs → compares against saved checksums; aborts on any mismatch.

    Returns True if all files pass.
    Raises SystemExit if any file has been modified.
    """
    os.makedirs(PROJECT_PATH, exist_ok=True)
    os.makedirs(OUTPUT_PATH,  exist_ok=True)

    # Paranoia check: make sure we are never writing inside the UO folder
    uo_real   = os.path.realpath(UO_PATH)
    proj_real = os.path.realpath(PROJECT_PATH)
    out_real  = os.path.realpath(OUTPUT_PATH)

    if out_real.startswith(uo_real):
        _abort("OUTPUT_PATH is inside UO_PATH — this would write to the game folder! "
               "Please set PROJECT_PATH to a different drive/folder.")

    if verbose:
        print("=" * 60)
        print("  SOURCE FILE INTEGRITY CHECK")
        print(f"  UO source : {UO_PATH}")
        print(f"  Output    : {OUTPUT_PATH}")
        print("=" * 60)

    # Collect current info
    current = {}
    for fname in SOURCE_FILES:
        fpath = os.path.join(UO_PATH, fname)
        if not os.path.exists(fpath):
            _abort(f"Source file not found: {fpath}\n"
                   f"Make sure your UO install is at {UO_PATH}")
        if verbose:
            print(f"  Checking {fname}...", end=" ", flush=True)
        info = _file_info(fpath)
        current[fname] = info
        if verbose:
            mb = info["size"] / 1024 / 1024
            print(f"{mb:.1f} MB  OK")

    # First run — save checksums
    if not os.path.exists(CHECKSUM_FILE):
        with open(CHECKSUM_FILE, "w") as f:   # writes to PROJECT_PATH, not UO_PATH
            json.dump({
                "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "uo_path": UO_PATH,
                "files": current,
            }, f, indent=2)
        if verbose:
            print(f"\n  [FIRST RUN] Checksums saved to:")
            print(f"  {CHECKSUM_FILE}")
            print("  These will be verified on every future run.")
    else:
        # Verify against saved
        with open(CHECKSUM_FILE, "r") as f:
            saved = json.load(f)

        errors = []
        for fname, info in current.items():
            if fname not in saved["files"]:
                continue  # new file added to list, skip
            ref = saved["files"][fname]
            if info["sha256"] != ref["sha256"]:
                errors.append(
                    f"  MODIFIED: {fname}\n"
                    f"    Expected SHA-256: {ref['sha256']}\n"
                    f"    Current  SHA-256: {info['sha256']}\n"
                    f"    Size change: {ref['size']:,} → {info['size']:,} bytes"
                )
            elif info["size"] != ref["size"]:
                errors.append(
                    f"  SIZE CHANGED: {fname}\n"
                    f"    Expected: {ref['size']:,} bytes\n"
                    f"    Current:  {info['size']:,} bytes"
                )

        if errors:
            _abort(
                "INTEGRITY CHECK FAILED — source UO files have changed!\n\n"
                + "\n\n".join(errors)
                + "\n\nThis tool should NEVER modify the source files.\n"
                  "If you did not change these files manually, something is wrong.\n"
                  "Do NOT proceed until you understand why the files changed."
            )

    if verbose:
        print("\n  All source files verified — originals untouched.")
        print("=" * 60 + "\n")

    return True


def safe_open_uo(filename):
    """
    The ONLY way this project opens UO source files.
    Guarantees read-only access and that the path is inside UO_PATH.
    """
    full_path = os.path.realpath(os.path.join(UO_PATH, filename))
    uo_real   = os.path.realpath(UO_PATH)

    # Ensure the resolved path is inside UO_PATH (prevent path traversal)
    if not full_path.startswith(uo_real):
        _abort(f"Path traversal detected: {filename} resolves outside UO_PATH")

    # Double-check we're not accidentally in the project folder
    proj_real = os.path.realpath(PROJECT_PATH)
    if full_path.startswith(proj_real):
        _abort(f"Tried to open a file from PROJECT_PATH as a source file: {full_path}")

    return open(full_path, "rb")   # READ-ONLY, always


def safe_output_path(filename):
    """
    Returns a safe output path inside OUTPUT_PATH.
    Verifies the result is never inside UO_PATH.
    """
    full_path = os.path.realpath(os.path.join(OUTPUT_PATH, filename))
    uo_real   = os.path.realpath(UO_PATH)

    if full_path.startswith(uo_real):
        _abort(f"Output path would write inside UO source folder: {full_path}")

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return full_path


def _abort(message):
    print("\n" + "!" * 60)
    print("  SAFETY ABORT")
    print("!" * 60)
    for line in message.split("\n"):
        print(f"  {line}")
    print("!" * 60 + "\n")
    sys.exit(1)


if __name__ == "__main__":
    # Run as standalone to just verify integrity
    verify_source_integrity(verbose=True)
    print("Source files are intact. Safe to proceed.")
