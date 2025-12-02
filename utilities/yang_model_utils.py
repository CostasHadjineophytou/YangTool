import os


def get_main_module_stmt(ctx, source_filename: str):
    """Select the module statement whose source filename matches the provided file."""
    basename = os.path.basename(source_filename)
    for m in ctx.modules.values():
        pos_ref = getattr(getattr(m, "pos", None), "ref", None)
        if pos_ref and os.path.basename(pos_ref) == basename:
            return m
    return next(iter(ctx.modules.values())) if ctx.modules else None


def find_first_substmt_arg(stmt, keyword: str) -> str:
    """Return the first substatement argument for 'keyword', or '-' if not present."""
    for s in getattr(stmt, "substmts", []) or []:
        if s.keyword == keyword:
            return s.arg
    return "-"


