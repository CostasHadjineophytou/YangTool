from typing import List
import os

try:
    from pyang import repository
except Exception as exc:
    raise


def build_repository(search_dirs: List[str]) -> repository.FileRepository:
    """Create a pyang FileRepository from a list of search directories."""
    search_path = os.pathsep.join([d for d in search_dirs if d]) if search_dirs else None
    return repository.FileRepository(search_path)

# from file
def add_module_to_context(ctx, yang_path: str) -> None:
    """Read a YANG file and register it with the given pyang Context."""
    filename = os.path.basename(yang_path)
    with open(yang_path, "r", encoding="utf-8") as f:
        text = f.read()
    ctx.add_module(filename, text)

# from in-memory text
def add_module_text(ctx, filename, text):
    """Register a YANG module's source text in the given pyang Context."""
    ctx.add_module(filename, text)
