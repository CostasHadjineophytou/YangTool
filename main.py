import argparse
import sys

import os
try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)

# Functions to load and validate the YANG module
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

# Functions to extract the summary of the YANG module
def get_main_module_stmt(ctx, source_filename):
    basename = os.path.basename(source_filename)
    for m in ctx.modules.values():
        pos_ref = getattr(getattr(m, "pos", None), "ref", None)
        if pos_ref and os.path.basename(pos_ref) == basename:
            return m
    return next(iter(ctx.modules.values())) if ctx.modules else None

def find_first_substmt_arg(stmt, keyword):
    for s in getattr(stmt, "substmts", []) or []:
        if s.keyword == keyword:
            return s.arg
    return "-"

def walk_model(stmt, parent_path=""):
    """Traverse the module statement to collect containers and leaves with paths and types"""
    containers = []
    leaves = []

    def _walk(s, path_prefix):
        if s.keyword == "container":
            current_path = f"{path_prefix}/{s.arg}" if path_prefix else s.arg
            containers.append(current_path)
            for child in getattr(s, "substmts", []) or []:
                _walk(child, current_path)
            return

        if s.keyword == "leaf":
            current_path = f"{path_prefix}/{s.arg}" if path_prefix else s.arg
            leaf_type = find_first_substmt_arg(s, "type") or "-"
            leaves.append((current_path, leaf_type))
            return

        # Dive into other structuring statements to find nested nodes
        for child in getattr(s, "substmts", []) or []:
            _walk(child, path_prefix)

    for sub in getattr(stmt, "substmts", []) or []:
        _walk(sub, parent_path)

    return containers, leaves

# Main function to validate and summarize the YANG module
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

    # Case: Validation passed, state success, print the summary of the YANG module.
    print("YANG validation passed.\nSee module summary below:\n")
    module_stmt = get_main_module_stmt(ctx, yang_file)
    if module_stmt:
        module_name = getattr(module_stmt, "arg", "-")
        namespace = find_first_substmt_arg(module_stmt, "namespace")
        print(f"Module: {module_name}")
        print(f"Namespace: {namespace}")
        containers, leaves = walk_model(module_stmt)
        print("Containers:")
        if containers:
            for c in sorted(containers):
                print(f"- {c}")
        else:
            print("- (none)")
        print("Leaves:")
        if leaves:
            for path, ltype in sorted(leaves, key=lambda x: x[0]):
                print(f"- {path}: {ltype}")
        else:
            print("- (none)")
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
