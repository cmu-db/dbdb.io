from __future__ import annotations

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple


def get_git_commit_metadata(
    repo_url: str,
    commit_id: str,
    *,
    timeout: int = 30,
) -> Tuple[str, datetime]:
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

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        def run(cmd: list[str]) -> str:
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

        timestamp = datetime.fromisoformat(timestamp_str).astimezone(timezone.utc)

        return message, timestamp