from urllib.parse import urlparse


def is_github_ui_url(url: str) -> bool:
    return "github.com" in urlparse(url).netloc and "/blob/" in url


def to_raw_github_url(url: str) -> str:
    """
    Convert a GitHub UI URL to the corresponding raw content URL.
    Example:
      https://github.com/{org}/{repo}/blob/{branch}/path/file.yang
      -> https://raw.githubusercontent.com/{org}/{repo}/{branch}/path/file.yang
    If the URL is not a GitHub blob URL, returns it unchanged.
    """
    parts = urlparse(url)
    path_parts = parts.path.split("/blob/")
    if len(path_parts) != 2:
        return url
    left, right = path_parts
    segments = left.strip("/").split("/")
    if len(segments) < 2:
        return url
    org, repo = segments[:2]
    branch_and_path = right.lstrip("/")
    return f"https://raw.githubusercontent.com/{org}/{repo}/{branch_and_path}"


