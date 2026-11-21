"""Compare a source tree with its backup (a folder or a .zip) and judge it.

Checks: missing files, extra files, size mismatches, optional sha256
mismatches, zip integrity (CRC test), and backup freshness (newest file
in the backup against a maximum age). Verdict is PROVEN only when every
check passes; anything else is NOT PROVEN with the reasons listed.
"""
import hashlib
import os
import time
import zipfile


def _hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def scan_source(root, use_hash):
    entries = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            with open(full, "rb") as handle:
                data = handle.read()
            entries[rel] = {"size": len(data),
                            "sha256": _hash_bytes(data) if use_hash else None}
    return entries


def scan_backup_folder(root, use_hash):
    return scan_source(root, use_hash)


def scan_backup_zip(path, use_hash):
    entries = {}
    newest = 0.0
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            return {}, 0.0, bad
        for info in archive.infolist():
            if info.is_dir():
                continue
            data = archive.read(info.filename)
            entries[info.filename] = {
                "size": len(data),
                "sha256": _hash_bytes(data) if use_hash else None}
            stamp = time.mktime(info.date_time + (0, 0, -1))
            newest = max(newest, stamp)
    return entries, newest, None


def newest_mtime(root):
    newest = 0.0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            newest = max(newest, os.path.getmtime(os.path.join(dirpath, name)))
    return newest


def compare(source, backup):
    missing = sorted(set(source) - set(backup))
    extra = sorted(set(backup) - set(source))
    size_mismatch = []
    hash_mismatch = []
    for rel in sorted(set(source) & set(backup)):
        if source[rel]["size"] != backup[rel]["size"]:
            size_mismatch.append(rel)
        elif (source[rel]["sha256"] is not None
              and source[rel]["sha256"] != backup[rel]["sha256"]):
            hash_mismatch.append(rel)
    return {"missing": missing, "extra": extra,
            "size_mismatch": size_mismatch, "hash_mismatch": hash_mismatch}


def prove(source_root, backup_path, max_age_hours=None, use_hash=False, now=None):
    now = time.time() if now is None else now
    source = scan_source(source_root, use_hash)
    corrupt_member = None
    if os.path.isdir(backup_path):
        backup = scan_backup_folder(backup_path, use_hash)
        freshest = newest_mtime(backup_path)
    elif zipfile.is_zipfile(backup_path):
        backup, freshest, corrupt_member = scan_backup_zip(backup_path, use_hash)
    else:
        raise ValueError("backup must be a folder or a .zip file")
    diff = compare(source, backup)
    age_hours = (now - freshest) / 3600 if freshest else None
    reasons = []
    if corrupt_member is not None:
        reasons.append(f"zip member fails CRC check: {corrupt_member}")
    if diff["missing"]:
        reasons.append(f"{len(diff['missing'])} files missing from backup")
    if diff["size_mismatch"]:
        reasons.append(f"{len(diff['size_mismatch'])} files differ in size")
    if diff["hash_mismatch"]:
        reasons.append(f"{len(diff['hash_mismatch'])} files differ in content")
    if max_age_hours is not None:
        if age_hours is None:
            reasons.append("backup is empty, freshness unknown")
        elif age_hours > max_age_hours:
            reasons.append(f"backup is {age_hours:.1f} hours old, over the {max_age_hours} hour limit")
    return {
        "proven": not reasons,
        "reasons": reasons,
        "source_files": len(source),
        "backup_files": len(backup),
        "backup_age_hours": None if age_hours is None else round(age_hours, 2),
        "diff": diff,
        "extra_files_note": f"{len(diff['extra'])} extra files in backup (not a failure)" if diff["extra"] else None,
    }
