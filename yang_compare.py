import argparse
import sys

import os
try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)

def build_repo(paths):
    search_path = os.pathsep.join([d for d in paths if d]) if paths else None
    return repository.FileRepository(search_path)

def add_to_ctx(ctx, yang_path):
    name = os.path.basename(yang_path)
    with open(yang_path, "r", encoding="utf-8") as f:
        ctx.add_module(name, f.read())

def get_module(ctx, src):
    base = os.path.basename(src)
    for m in ctx.modules.values():
        pos_ref = getattr(getattr(m, "pos", None), "ref", None)
        if pos_ref and os.path.basename(pos_ref) == base:
            return m
    return next(iter(ctx.modules.values())) if ctx.modules else None

def first_sub_arg(stmt, keyword):
    for s in getattr(stmt, "substmts", []) or []:
        if s.keyword == keyword:
            return s.arg
    return "-"

def collect(stmt):
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
            leaves[path] = first_sub_arg(s, "type") or "-"
            return

        if hasattr(s, "substmts") and getattr(s, "substmts"):
            for ch in s.substmts:
                _walk(ch, prefix)

    for sub in getattr(stmt, "substmts", []) or []:
        _walk(sub, "")

    return containers, leaves

def validate_and_collect(yang_file, include_paths):
    repo = build_repo([os.path.dirname(os.path.abspath(yang_file))] + include_paths)
    ctx = pyang_context.Context(repo)
    add_to_ctx(ctx, yang_file)
    ctx.validate()

    if getattr(ctx, "errors", None):
        msgs = "; ".join(f"{getattr(p, 'ref', '<input>')}: {t}: {m}" for p, t, m in ctx.errors)
        raise ValueError(f"Validation failed for {yang_file}: {msgs}")

    mod = get_module(ctx, yang_file)
    if not mod:
        raise ValueError(f"No module found in {yang_file}")

    return collect(mod)

def compare_sets(old, new):
    removed = old - new
    added = new - old
    return removed, added

def compare_dicts(old, new):
    old_keys, new_keys = set(old.keys()), set(new.keys())
    removed = old_keys - new_keys
    added = new_keys - old_keys
    changed = {k for k in old_keys & new_keys if old[k] != new[k]}
    return removed, added, changed


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Compare two YANG files (containers and leaves)")
    parser.add_argument("old", help="Old/base YANG file")
    parser.add_argument("new", help="New/updated YANG file")
    parser.add_argument("-p", "--path", action="append", default=[], help="Additional include/import path")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    try:
        old_cont, old_leaves = validate_and_collect(args.old, args.path)
        new_cont, new_leaves = validate_and_collect(args.new, args.path)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 2

    c_removed, c_added = compare_sets(old_cont, new_cont)
    l_removed, l_added, l_changed = compare_dicts(old_leaves, new_leaves)

    print("Containers:")
    print("- Added:")
    for i in sorted(c_added) or ["(none)"]:
        print(f"  - {i}")
    print("- Removed:")
    for i in sorted(c_removed) or ["(none)"]:
        print(f"  - {i}")

    print("Leaves:")
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

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
