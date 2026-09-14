"""HTTP downloader for model layers (resume, retries, SHA-256)."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional

import httpx
from tqdm import tqdm

from wavhost.config import (
    BUFFER_SIZE,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_MAX_RETRIES,
    DOWNLOAD_TIMEOUT,
    DOWNLOAD_USER_AGENT,
    HASH_ALGORITHM,
)
from wavhost.exceptions import DownloadError
from wavhost.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": DOWNLOAD_USER_AGENT,
    "Accept": "*/*",
}


def compute_file_hash(path: Path) -> str:
    """Compute the configured content hash of a file."""
    hash_obj = hashlib.new(HASH_ALGORITHM)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(BUFFER_SIZE), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def download_file(
    url: str,
    dest: Path,
    *,
    expected_sha256: Optional[str] = None,
    show_progress: bool = True,
    max_retries: int = DOWNLOAD_MAX_RETRIES,
) -> str:
    """Download a file with resume support, retries, and hash verification.

    Args:
        url: Source URL (any plain HTTPS host)
        dest: Destination path (partial downloads are resumed here)
        expected_sha256: Optional digest to verify after download
        show_progress: Whether to show a progress bar
        max_retries: Number of retry attempts after disconnects

    Returns:
        Hex SHA-256 digest of the downloaded file

    Raises:
        DownloadError: If the download fails or the digest mismatches
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")

    # Resume into the partial file; finished files are moved to dest.
    if dest.exists() and not partial.exists():
        digest = compute_file_hash(dest)
        if expected_sha256 and digest != expected_sha256:
            dest.unlink()
        else:
            return digest

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            digest = _download_attempt(
                url,
                dest,
                partial,
                expected_sha256=expected_sha256,
                show_progress=show_progress,
            )
            return digest
        except (httpx.HTTPError, OSError, DownloadError) as e:
            last_error = e
            logger.warning(
                f"Download attempt {attempt}/{max_retries} failed for {url}: {e}"
            )
            if attempt < max_retries:
                # Back off harder on connection resets (common with HF on Windows).
                delay = min(2 ** (attempt - 1), 60)
                time.sleep(delay)

    raise DownloadError(
        f"Failed to download {url} after {max_retries} attempts: {last_error}"
    )


def _download_attempt(
    url: str,
    dest: Path,
    partial: Path,
    *,
    expected_sha256: Optional[str],
    show_progress: bool,
) -> str:
    existing = partial.stat().st_size if partial.exists() else 0
    headers = dict(_DEFAULT_HEADERS)
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"

    timeout = httpx.Timeout(DOWNLOAD_TIMEOUT, connect=30.0)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=_DEFAULT_HEADERS,
    ) as client:
        with client.stream("GET", url, headers=headers) as response:
            if response.status_code == 416:
                # Partial is already complete according to the server.
                pass
            elif existing > 0 and response.status_code == 200:
                # Server ignored Range — restart from scratch.
                existing = 0
                if partial.exists():
                    partial.unlink()
            elif response.status_code not in (200, 206):
                raise DownloadError(
                    f"HTTP {response.status_code} downloading {url}"
                )

            total_header = response.headers.get("Content-Length")
            content_range = response.headers.get("Content-Range")
            if content_range and "/" in content_range:
                try:
                    total_size = int(content_range.rsplit("/", 1)[1])
                except ValueError:
                    total_size = existing + (int(total_header) if total_header else 0)
            elif total_header:
                total_size = (
                    existing + int(total_header)
                    if response.status_code == 206
                    else int(total_header)
                )
            else:
                total_size = None

            mode = "ab" if existing > 0 and response.status_code == 206 else "wb"
            if mode == "wb" and partial.exists():
                partial.unlink()
                existing = 0

            if response.status_code != 416:
                progress = (
                    tqdm(
                        total=total_size,
                        initial=existing,
                        unit="B",
                        unit_scale=True,
                        desc=dest.name,
                    )
                    if show_progress
                    else None
                )
                try:
                    with open(partial, mode) as f:
                        for chunk in response.iter_bytes(DOWNLOAD_CHUNK_SIZE):
                            if not chunk:
                                continue
                            f.write(chunk)
                            # Use `is not None` — tqdm with total=None raises on bool().
                            if progress is not None:
                                progress.update(len(chunk))
                finally:
                    if progress is not None:
                        progress.close()

    if not partial.exists():
        raise DownloadError(f"Download produced no file for {url}")

    digest = compute_file_hash(partial)
    if expected_sha256 and digest != expected_sha256:
        partial.unlink(missing_ok=True)
        raise DownloadError(
            f"SHA-256 mismatch for {dest.name}: "
            f"expected {expected_sha256}, got {digest}"
        )

    if dest.exists():
        dest.unlink()
    partial.replace(dest)
    return digest
