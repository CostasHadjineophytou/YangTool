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


def http_get_text(url):
    """Fetch a URL and return its text content, raising on HTTP errors."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def add_module_text(ctx, filename, text):
    """Register a YANG module's source text in the given pyang Context."""
    ctx.add_module(filename, text)


def infer_filename_from_url(url):
    """Infer a filename from the URL path (e.g., '.../file.yang' -> 'file.yang')."""
    return os.path.basename(urlparse(url).path) or "module.yang"


def extract_imports(yang_text):
    """Extract module names from 'import' and 'include' statements (naive line-based scan)."""
    imports = []
    includes = []
    for line in yang_text.splitlines():
        line = line.strip()
        if line.startswith("import "):
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


def try_fetch_dependency(name, base_urls):
    """Try to fetch a dependency '<name>.yang' from each base URL; return (filename, text) or None."""
    for base in base_urls:
        candidate = urljoin(base if base.endswith("/") else base + "/", f"{name}.yang")
        try:
            text = http_get_text(candidate)
            return infer_filename_from_url(candidate), text
        except Exception:
            continue
    return None


def resolve_dependencies(ctx, roots, import_bases, visited=None):
    """
    Recursively fetch and add imported/included modules into the context.

    Args:
        ctx: pyang Context to add modules to.
        roots: top-level import/include names to resolve.
        import_bases: base URLs to try when fetching '<name>.yang'.
        visited: set used to avoid cycles.

    Returns:
        (found_paths, missing) where:
          - found_paths is a list like ['A', 'A/B', ...] showing transitive paths
          - missing lists dependency paths that could not be fetched
    """
    if visited is None:
        visited = set()
    found_paths = set()
    missing = []

    def _walk(name, path_prefix):
        if name in visited:
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
        child_imports, child_includes = extract_imports(dep_text)
        for child in list(dict.fromkeys(child_imports + child_includes)):
            _walk(child, f"{path_prefix}/{child}")

    for root in roots:
        _walk(root, root)
    return list(found_paths), missing


def validate_and_print_transitive_dependencies(module_url, import_bases, ignore_missing):
    """Validate a remote YANG module and print its transitive dependency tree and pass/fail status."""
    if is_github_ui_url(module_url):
        module_url = to_raw_github_url(module_url)

    try:
        main_text = http_get_text(module_url)
    except Exception as e:
        print(f"Failed to fetch module: {e}", file=sys.stderr)
        return 4

    parsed = urlparse(module_url)
    module_dir = module_url.rsplit("/", 1)[0] + "/" if "/" in parsed.path else module_url
    derived_bases = [module_dir]
    if import_bases:
        derived_bases.extend(import_bases)

    repo = repository.FileRepository("")
    ctx = pyang_context.Context(repo)

    main_filename = infer_filename_from_url(module_url)
    add_module_text(ctx, main_filename, main_text)

    found_paths = []
    missing_paths = []
    imports, includes = extract_imports(main_text)
    needed = list(dict.fromkeys(imports + includes))
    if needed:
        found_paths, missing_paths = resolve_dependencies(ctx, needed, derived_bases)

    ctx.validate()

    errors = getattr(ctx, "errors", []) or []
    if errors and ignore_missing:
        filtered = []
        for pos, etype, msg in errors:
            if str(etype) == "MODULE_NOT_FOUND":
                continue
            filtered.append((pos, etype, msg))
        errors = filtered

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
        print("YANG validation failed.")
        return 1
    print("YANG validation passed.")
    return 0


def parse_args(argv):
    """Parse CLI arguments for validating a remote YANG module and printing dependencies."""
    p = argparse.ArgumentParser(description="Validate a remote YANG module and print its transitive dependency tree")
    p.add_argument("url", help="HTTP(S) URL to the YANG module (GitHub Raw or standard URL)")
    p.add_argument(
        "-u",
        "--import-base",
        action="append",
        default=[],
        help="Base URL to search for imports/includes (repeatable). If omitted, the module's own directory is used.",
    )
    p.add_argument(
        "--ignore-missing-imports",
        action="store_true",
        help="Do not fail on MODULE_NOT_FOUND; filters missing imports after validation",
    )
    return p.parse_args(argv)


def main(argv):
    """CLI entrypoint: parse args and run validation+dependency printing."""
    args = parse_args(argv)
    return validate_and_print_transitive_dependencies(args.url, args.import_base, args.ignore_missing_imports)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


