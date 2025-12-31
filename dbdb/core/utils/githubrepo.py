from github import Github, Auth
from typing import Dict, Optional
import re

def get_metadata(repo_url: str, token: Optional[str] = None) -> Dict:
    """
    Retrieve metadata about a GitHub repository using PyGithub (official GitHub API library).

    Args:
        repo_url: GitHub repository URL (e.g., 'https://github.com/owner/repo')
        token: Optional GitHub personal access token for authentication and higher rate limits

    Returns:
        Dictionary containing repo metadata

    Raises:
        ValueError: If the URL is invalid
        Exception: If API request fails
    """
    # Extract owner and repo name from URL
    pattern = r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
    match = re.search(pattern, repo_url)

    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    owner, repo_name = match.groups()

    # Initialize GitHub client
    if token:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    else:
        g = Github()  # Unauthenticated (60 requests/hour)

    try:
        # Get repository object
        repo = g.get_repo(f"{owner}/{repo_name}")

        # Get total pull requests count (open + closed)
        total_prs = repo.get_pulls(state='all').totalCount

        # Get branches count
        total_branches = repo.get_branches().totalCount

        # Get latest commit timestamp across all branches
        # We'll check the default branch's latest commit
        latest_commit = repo.get_commits()[0]
        latest_commit_timestamp = latest_commit.commit.committer.date.isoformat()

        # Get total commits on default branch
        total_commits = repo.get_commits().totalCount

        # Compile metadata
        metadata = {
            'stars': repo.stargazers_count,
            'issues': repo.open_issues_count,  # Note: includes open PRs
            'pull_requests': total_prs,
            'commits': total_commits,
            'branches': total_branches,
            'watchers': repo.subscribers_count,
            'forks': repo.forks_count,
            'default_branch': repo.default_branch,
            'latest_commit_timestamp': latest_commit_timestamp,
            'repo_name': repo.full_name,
            'description': repo.description,
            'language': repo.language,
            'created_at': repo.created_at.isoformat(),
            'updated_at': repo.updated_at.isoformat()
        }

        return metadata

    finally:
        # Close connection
        g.close()