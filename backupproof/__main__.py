"""CLI: python -m backupproof SOURCE BACKUP [--max-age-hours H] [--hash] [--json]"""
import argparse
import json
import sys

from .core import prove


def main(argv=None):
    parser = argparse.ArgumentParser(prog="backupproof", description="Prove a backup matches its source.")
    parser.add_argument("source", help="Source folder")
    parser.add_argument("backup", help="Backup folder or .zip file")
    parser.add_argument("--max-age-hours", type=float, help="Fail if the backup is older than this")
    parser.add_argument("--hash", action="store_true", help="Compare sha256 content hashes, not just sizes")
    parser.add_argument("--json", action="store_true", help="Print the verdict as JSON")
    args = parser.parse_args(argv)

    try:
        result = prove(args.source, args.backup, max_age_hours=args.max_age_hours,
                       use_hash=args.hash)
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"source files: {result['source_files']}  backup files: {result['backup_files']}  "
              f"backup age: {result['backup_age_hours']} hours")
        if result["extra_files_note"]:
            print(result["extra_files_note"])
        if result["proven"]:
            print("PROVEN: the backup matches the source.")
        else:
            print("NOT PROVEN:")
            for reason in result["reasons"]:
                print(f"  - {reason}")
    return 0 if result["proven"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
