#!/use/bin/env python3
# ruff: noqa: T201
from __future__ import annotations

import argparse
from pathlib import Path

from ..ipynb import ipynb2jupytext, load_ipynb


def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert ipynb to a jupytext percent format (.ju.py).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("ipynb_path", help="Path to ipynb file")
    parser.add_argument(
        "output_jupy_path",
        nargs="?",
        help="Path to output jupynium file. "
        "If not specified, use file name of ipynb file or print to stdout (--stdout)",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Do not ask for confirmation"
    )
    parser.add_argument(
        "-c", "--code_only", action="store_true", help="Only convert code cells"
    )
    parser.add_argument("-s", "--stdout", action="store_true", help="Print to stdout")
    return parser


def check_args(args, parser):
    if args.stdout and args.yes:
        parser.error("Either one of --stdout or --yes can be specified")

    if args.output_jupy_path is not None and args.stdout:
        parser.error("Either one of --stdout or output_jupy_path can be specified")


def main():
    parser = get_parser()
    args = parser.parse_args()
    check_args(args, parser)

    ipynb = load_ipynb(args.ipynb_path)
    jupy = ipynb2jupytext(ipynb, code_only=args.code_only)

    if args.stdout:
        for line in jupy:
            print(line)
    else:
        if args.output_jupy_path is None:
            output_jupy_path = Path(args.ipynb_path).with_suffix(".ju.py")
        else:
            output_jupy_path = Path(args.output_jupy_path)

        output_jupy_path.parent.mkdir(parents=True, exist_ok=True)

        if output_jupy_path.is_file() and not args.yes:
            print(f"Do you want to overwrite {output_jupy_path}?")
            answer = input("y/n: ")
            if answer != "y":
                print("Aborted")
                return

        with open(output_jupy_path, "w") as f:
            for line in jupy:
                f.write(line)
                f.write("\n")

        print(f'Converted "{args.ipynb_path}" to "{output_jupy_path}"')


if __name__ == "__main__":
    main()
