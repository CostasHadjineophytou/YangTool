import argparse
import os
import sys
from urllib.parse import urljoin, urlparse
from utilities.web_address_converter import is_github_ui_url, to_raw_github_url

import requests

try:
    from pyang import repository, context as pyang_context
except Exception:
    print("pyang not installed. Run: pip install pyang", file=sys.stderr)
    sys.exit(2)


def http_get_text(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def add_module_text(ctx: pyang_context.Context, filename: str, text: str) -> None:
    ctx.add_module(filename, text)


def infer_filename_from_url(url: str) -> str:
    return os.path.basename(urlparse(url).path) or "module.yang"


def extract_imports(yang_text: str):
    # naive extraction; good enough for github raw content
    # returns list of module names (without .yang)
    imports = []
    includes = []
    for line in yang_text.splitlines():
        line = line.strip()
        if line.startswith("import "):
            # import <name> {
            try:
                name = line.split()[1]
                name = name.rstrip("{").strip()
                imports.append(name)
            except Exception:
                continue
        elif line.startswith("include "):
            try:
                name = line.split()[1]
                name = name.rstrip("{").strip()
                includes.append(name)
            except Exception:
                continue
    return imports, includes


def try_fetch_dependency(name: str, base_urls: list[str]) -> tuple[str, str] | None:
    # Try each base URL by appending "<name>.yang"
    for base in base_urls:
        candidate = urljoin(base if base.endswith("/") else base + "/", f"{name}.yang")
        try:
            text = http_get_text(candidate)
            return infer_filename_from_url(candidate), text
        except Exception:
            continue
    return None


def resolve_dependencies(
    ctx: pyang_context.Context,
    roots: list[str],
    import_bases: list[str],
    visited: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Recursively fetch and add imported/included modules into the context.
    Returns:
      - found_paths: list of 'A', 'A/B', ... for fetched modules
      - missing: list of module names that could not be fetched
    """
    if visited is None:
        visited = set()
    found_paths: set[str] = set()
    missing: list[str] = []

    def _walk(name: str, path_prefix: str):
        if name in visited:
            # Even if already fetched via another branch, record a top-level import reference
            if "/" not in path_prefix:
                found_paths.add(path_prefix)
            return
        visited.add(name)
        fetched = try_fetch_dependency(name, import_bases)
        if not fetched:
            missing.append(path_prefix)
            return
        dep_filename, dep_text = fetched
        add_module_text(ctx, dep_filename, dep_text)
        found_paths.add(path_prefix)
        # Recurse into this dependency's imports/includes
        child_imports, child_includes = extract_imports(dep_text)
        for child in list(dict.fromkeys(child_imports + child_includes)):
            _walk(child, f"{path_prefix}/{child}")

    for root in roots:
        _walk(root, root)
    return list(found_paths), missing


def get_main_module_stmt(ctx: pyang_context.Context, source_filename: str):
    basename = os.path.basename(source_filename)
    for m in ctx.modules.values():
        pos_ref = getattr(getattr(m, "pos", None), "ref", None)
        if pos_ref and os.path.basename(pos_ref) == basename:
            return m
    return next(iter(ctx.modules.values())) if ctx.modules else None


def find_first_substmt_arg(stmt, keyword: str) -> str:
    for s in getattr(stmt, "substmts", []) or []:
        if s.keyword == keyword:
            return s.arg
    return "-"


def walk_model(stmt, parent_path: str = ""):
    containers = []
    leaves = []

    def _walk(s, path_prefix: str):
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
        for child in getattr(s, "substmts", []) or []:
            _walk(child, path_prefix)

    for sub in getattr(stmt, "substmts", []) or []:
        _walk(sub, parent_path)

    return containers, leaves


def validate_online(module_url: str, import_bases: list[str], ignore_missing: bool) -> int:
    if is_github_ui_url(module_url):
        module_url = to_raw_github_url(module_url)

    # Fetch main module
    try:
        main_text = http_get_text(module_url)
    except Exception as e:
        print(f"Failed to fetch module: {e}", file=sys.stderr)
        return 4

    # Derive a default base URL from the module URL (directory containing the file)
    parsed = urlparse(module_url)
    module_dir = module_url.rsplit("/", 1)[0] + "/" if "/" in parsed.path else module_url
    # Always try the module's own directory first, then any user-provided bases
    derived_bases = [module_dir]
    if import_bases:
        # keep order: derived first, then user-provided
        derived_bases.extend(import_bases)

    # Build an empty repository (string path required); we will feed modules via add_module
    repo = repository.FileRepository("")
    ctx = pyang_context.Context(repo)

    main_filename = infer_filename_from_url(module_url)
    add_module_text(ctx, main_filename, main_text)

    # Optionally attempt to fetch imports/includes from provided base URLs (recursively)
    found_paths: list[str] = []
    missing_paths: list[str] = []
    if derived_bases:
        imports, includes = extract_imports(main_text)
        needed = list(dict.fromkeys(imports + includes))
        if needed:
            found_paths, missing_paths = resolve_dependencies(ctx, needed, derived_bases)

    ctx.validate()

    errors = getattr(ctx, "errors", []) or []
    if errors and ignore_missing:
        # Filter out missing-module errors
        filtered = []
        for pos, etype, msg in errors:
            if str(etype) == "MODULE_NOT_FOUND":
                continue
            filtered.append((pos, etype, msg))
        errors = filtered

    # Print dependency summary before results
    print("Dependencies (fetched):")
    if found_paths:
        for p in sorted(found_paths):
            print(f"- {p}")
    else:
        print("- (none)")
    if missing_paths:
        print("Dependencies (missing):")
        for p in sorted(missing_paths):
            print(f"- {p}")

    if errors:
        print("YANG validation failed:")
        for pos, etype, msg in errors:
            where = getattr(pos, "ref", "<input>") if pos else "<input>"
            print(f"- {where}: {etype}: {msg}")
        return 1

    print("YANG validation passed.\nSee module summary below:\n")
    module_stmt = get_main_module_stmt(ctx, main_filename)
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
    p = argparse.ArgumentParser(description="Validate a remote YANG module by URL")
    p.add_argument("url", help="HTTP(S) URL to the YANG module (use Raw GitHub URL or standard URL)")
    p.add_argument(
        "-u",
        "--import-base",
        action="append",
        default=[],
        help="Base URL to search for imports/includes (repeatable). Example: https://raw.githubusercontent.com/YangModels/yang/main/vendor/cisco/xr/",
    )
    p.add_argument(
        "--ignore-missing-imports",
        action="store_true",
        help="Do not fail on MODULE_NOT_FOUND; filters missing imports after validation",
    )
    return p.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    return validate_online(args.url, args.import_base, args.ignore_missing_imports)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


