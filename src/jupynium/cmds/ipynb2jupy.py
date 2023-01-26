#!/use/bin/env python3
from __future__ import annotations

import argparse
import os

from ..ipynb import ipynb2jupy, load_ipynb


def get_parser():
    parser = argparse.ArgumentParser(
        description="Convert ipynb to a jupynium file (.ju.py)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("ipynb_path", help="Path to ipynb file")
    parser.add_argument(
        "output_jupy_path",
        nargs="?",
        help="Path to output jupynium file. If not specified, use file name of ipynb file or print to stdout (--stdout)",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Do not ask for confirmation"
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
    jupy = ipynb2jupy(ipynb)

    if args.stdout:
        for line in jupy:
            print(line)
    else:
        output_jupy_path = args.output_jupy_path
        if output_jupy_path is None:
            output_jupy_path = os.path.splitext(args.ipynb_path)[0] + ".ju.py"

        os.makedirs(os.path.dirname(os.path.realpath(output_jupy_path)), exist_ok=True)

        if os.path.isfile(output_jupy_path) and not args.yes:
            print("Do you want to overwrite {}?".format(output_jupy_path))
            answer = input("y/n: ")
            if answer != "y":
                print("Aborted")
                return

        with open(output_jupy_path, "w") as f:
            for line in jupy:
                f.write(line)
                f.write("\n")

        print('Converted "{}" to "{}"'.format(args.ipynb_path, output_jupy_path))


if __name__ == "__main__":
    main()
