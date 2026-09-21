"""Create/verify a private offline bundle or restore into an empty rehearsal database."""

import argparse
import json
import os
from pathlib import Path

from retrievec.registry.backup import backup, restore, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--store", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--quiesced", action="store_true")
    check = commands.add_parser("verify")
    check.add_argument("bundle", type=Path)
    rehearsal = commands.add_parser("restore")
    rehearsal.add_argument("bundle", type=Path)
    rehearsal.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "backup":
        result = backup(
            os.environ["RETRIEVEC_DSN"], args.store, args.output, quiesced=args.quiesced
        )
    elif args.action == "restore":
        result = restore(os.environ["RETRIEVEC_RESTORE_DSN"], args.bundle, args.store)
    else:
        manifest = verify(args.bundle)
        result = {"files": len(manifest["files"]), "verified": True}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
