import argparse
import sys

import os
try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)

def build_repository(search_dirs):
    """Helper function to build the repository"""
    search_path = os.pathsep.join([d for d in search_dirs if d]) if search_dirs else None
    # Use pyang's built in FileRepository to build the repository
    return repository.FileRepository(search_path)

def add_module_to_context(ctx, yang_path):
    """Read a YANG file and register it with the given pyang context"""
    filename = os.path.basename(yang_path)
    with open(yang_path, "r", encoding="utf-8") as f:
        text = f.read()
    # Use pyang's built in add_module to add the module to the context
    ctx.add_module(filename, text)


def validate_and_summarize(yang_file, include_paths):
    """Function to validate and summarize the YANG module"""
    # Only validates for now, no summary yet!

    include_dirs = [os.path.dirname(os.path.abspath(yang_file))] + (include_paths or [])

    # Using pyang's repository and context to validate the YANG module via helper functions defined above
    repo = build_repository(include_dirs)
    ctx = pyang_context.Context(repo)
    add_module_to_context(ctx, yang_file)

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
    """Helper function to parse the arguments"""
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
