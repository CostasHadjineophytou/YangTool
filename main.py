import argparse
import sys

import os
try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)


def validate_and_summarize(yang_file, include_paths):
    # Only validates for now, no summary yet!
    include_dirs = [os.path.dirname(os.path.abspath(yang_file))] + (include_paths or [])
    search_path = os.pathsep.join([d for d in include_dirs if d]) if include_dirs else None

    # Using pyang's repository and context to validate the YANG module
    repo = repository.FileRepository(search_path)
    ctx = pyang_context.Context(repo)

    with open(yang_file, "r", encoding="utf-8") as f:
        ctx.add_module(os.path.basename(yang_file), f.read())

    ctx.validate()

    # Case: Validation failed
    if getattr(ctx, "errors", None):
        print("YANG validation failed:")
        for pos, etype, msg in ctx.errors:
            where = getattr(pos, "ref", "<input>") if pos else "<input>"
            print(f"- {where}: {etype}: {msg}")
        return 1

    # Case: Validation passed
    print("YANG validation passed.")
    return 0


def parse_args(argv):
    p = argparse.ArgumentParser(description="Mini YANG Inspector")
    p.add_argument("yang", help="Path to a .yang file")
    p.add_argument("-p", "--path", action="append", default=[], help="Additional YANG search path")
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    if not os.path.isfile(args.yang):
        print(f"File not found: {args.yang}", file=sys.stderr)
        return 3
    return validate_and_summarize(args.yang, args.path)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
