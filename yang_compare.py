import argparse
import sys

import os
try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)
from utilities.pyang_utils import build_repository, add_module_to_context
from utilities.yang_model_utils import get_main_module_stmt, find_first_substmt_arg

def collect(stmt):
    """Walk the module statement and collect containers (set of paths) and leaves (path->type)."""
    containers = set()
    leaves = {}

    def _walk(s, prefix):
        if s.keyword == "container":
            path = f"{prefix}/{s.arg}" if prefix else s.arg
            containers.add(path)
            for ch in getattr(s, "substmts", []) or []:
                _walk(ch, path)
            return

        if s.keyword == "leaf":
            path = f"{prefix}/{s.arg}" if prefix else s.arg
            leaves[path] = find_first_substmt_arg(s, "type") or "-"
            return

        if hasattr(s, "substmts") and getattr(s, "substmts"):
            for ch in s.substmts:
                _walk(ch, prefix)

    for sub in getattr(stmt, "substmts", []) or []:
        _walk(sub, "")

    return containers, leaves

def validate_and_collect(yang_file, include_paths):
    """Validate a YANG file, select its main module, and return collected containers/leaves."""
    repo = build_repository([os.path.dirname(os.path.abspath(yang_file))] + include_paths)
    ctx = pyang_context.Context(repo)
    add_module_to_context(ctx, yang_file)
    ctx.validate()

    if getattr(ctx, "errors", None):
        msgs = "; ".join(f"{getattr(p, 'ref', '<input>')}: {t}: {m}" for p, t, m in ctx.errors)
        raise ValueError(f"Validation failed for {yang_file}: {msgs}")

    mod = get_main_module_stmt(ctx, yang_file)
    if not mod:
        raise ValueError(f"No module found in {yang_file}")

    return collect(mod)

def compare_sets(old, new):
    """Return (removed, added) elements comparing two sets."""
    removed = old - new
    added = new - old
    return removed, added

def compare_dicts(old, new):
    """Compare two dicts by keys and values; return (removed_keys, added_keys, changed_value_keys)."""
    old_keys, new_keys = set(old.keys()), set(new.keys())
    removed = old_keys - new_keys
    added = new_keys - old_keys
    changed = {k for k in old_keys & new_keys if old[k] != new[k]}
    return removed, added, changed


def parse_args(argv):
    """Parse CLI arguments for comparing two YANG files."""
    parser = argparse.ArgumentParser(description="Compare two YANG files (containers and leaves)")
    parser.add_argument("old", help="Old/base YANG file")
    parser.add_argument("new", help="New/updated YANG file")
    parser.add_argument("-p", "--path", action="append", default=[], help="Additional include/import path")
    return parser.parse_args(argv)


def main(argv):
    """CLI entrypoint: validate both files, compute and print structural diffs."""
    args = parse_args(argv)
    try:
        old_cont, old_leaves = validate_and_collect(args.old, args.path)
        new_cont, new_leaves = validate_and_collect(args.new, args.path)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    c_removed, c_added = compare_sets(old_cont, new_cont)
    l_removed, l_added, l_changed = compare_dicts(old_leaves, new_leaves)

    print("\nContainers:")
    print("- Added:")
    for i in sorted(c_added) or ["(none)"]:
        print(f"  - {i}")
    print("- Removed:")
    for i in sorted(c_removed) or ["(none)"]:
        print(f"  - {i}")

    print("\nLeaves:")
    print("- Added:")
    for i in sorted(l_added) or ["(none)"]:
        print(f"  - {i}: {new_leaves.get(i, '-')}")
    print("- Removed:")
    for i in sorted(l_removed) or ["(none)"]:
        print(f"  - {i}: {old_leaves.get(i, '-')}")
    print("- Changed type:")
    for i in sorted(l_changed) or ["(none)"]:
        if i == "(none)":
            print("  - (none)")
        else:
            print(f"  - {i}: {old_leaves[i]} -> {new_leaves[i]}")
    print("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
