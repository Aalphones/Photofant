"""Atomic file writes — never leave a half-written file at a tracked path.

A plain `shutil.copy2` writes straight to the destination. If the process is
killed mid-copy (or the disk fills), a truncated file is left at the exact path
a DB row points at — a corrupted asset the FS↔DB reconcile only catches after
the fact, when the thumbnail still shows but the lightbox can't decode the file.

The fix: write to a sibling temp file in the destination's own directory (same
volume, so the final swap is atomic), then `os.replace` it into place. The
destination only ever appears complete or not at all. On any error the temp
file is removed and the original destination is left untouched.
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path


def _temp_sibling(dest: Path) -> Path:
    """A hidden temp name next to dest — same directory guarantees same volume.

    The `.part` suffix is deliberately not an image extension, so a temp file
    orphaned by a hard process kill never shows up as an orphaned image in the
    reconcile walk.
    """
    return dest.with_name(f".{dest.name}.{uuid.uuid4().hex}.part")


def atomic_copy(source: Path, dest: Path) -> Path:
    """Copy source → dest so dest never exists in a half-written state.

    Writes to a temp file in dest's directory, then swaps it in with `os.replace`
    (atomic on the same volume, overwrites an existing dest). Any error removes
    the temp file and re-raises, leaving dest as it was. Returns dest.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = _temp_sibling(dest)
    try:
        shutil.copy2(str(source), str(tmp))
        os.replace(str(tmp), str(dest))
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return dest
