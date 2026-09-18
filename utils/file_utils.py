import os
from urllib.parse import urlparse


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def normalize_path(path):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(str(path))))


def build_target_path(url, filename=None, save_dir=None):
    parsed = urlparse(url)
    if filename:
        target_name = str(filename).strip()
    else:
        target_name = os.path.basename(parsed.path) or "download_file"
    target_dir = normalize_path(save_dir or os.getcwd())
    ensure_dir(target_dir)
    return os.path.join(target_dir, target_name)
