"""Inspect interrupted load journals without contacting the workspace."""

import argparse
import json

from retrievec.evaluation.load_recovery import recover

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    print(json.dumps(recover(parser.parse_args().directory), indent=2))
