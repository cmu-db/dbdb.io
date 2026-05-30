from __future__ import annotations

import logging
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

LOG = logging.getLogger(__name__)


def get_git_commit_metadata(
    repo_url: str,
    commit_id: str,
    *,
    timeout: int = 30,
) -> tuple[str, datetime]:
    """
    Return the commit message and commit timestamp for a commit
    from any Git repository reachable via HTTPS.

    Parameters
    ----------
    repo_url : str
        Git repository HTTPS URL
    commit_id : str
        Commit SHA (full or abbreviated)
    timeout : int
        Timeout for each git command (seconds)

    Returns
    -------
    (message, timestamp) : (str, datetime)
        Commit message and commit timestamp (UTC)

    Raises
    ------
    RuntimeError
        If the commit cannot be fetched or inspected
    """

    LOG.debug("Fetching commit %s from %s", commit_id, repo_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        def run(cmd: list[str]) -> str:
            LOG.debug("Running: %s", ' '.join(cmd))
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                    check=True,
                )
                return result.stdout
            except subprocess.CalledProcessError as e:
                raise RuntimeError(e.stderr.strip()) from e

        # Initialize a bare repository
        run(["git", "init", "--bare"])

        # Fetch only the requested commit
        run([
            "git",
            "fetch",
            "--depth=1",
            repo_url,
            commit_id,
        ])

        # Extract commit timestamp (%cI = strict ISO 8601)
        timestamp_str = run([
            "git",
            "show",
            "-s",
            "--format=%cI",
            commit_id,
        ]).strip()

        # Extract full commit message
        message = run([
            "git",
            "show",
            "-s",
            "--format=%B",
            commit_id,
        ]).rstrip()

        timestamp = datetime.fromisoformat(timestamp_str).astimezone(UTC)
        LOG.debug("Commit %s: timestamp=%s message=%r", commit_id, timestamp, message[:80])

        return message, timestamp