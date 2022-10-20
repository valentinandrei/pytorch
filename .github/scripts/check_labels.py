#!/usr/bin/env python3
"""check_labels.py"""

from typing import Any, List
from datetime import datetime, timedelta

from export_pytorch_labels import get_pytorch_labels
from gitutils import (
    get_git_remote_name,
    get_git_repo_dir,
    GitRepo,
)
from trymerge import (
    _fetch_url,
    gh_post_pr_comment,
    GitHubPR,
)


BOT_AUTHORS = ["github-actions", "pytorchmergebot", "pytorch-bot"]

ERR_MSG_TITLE = "This PR needs a label"
ERR_MSG = (
    f"# {ERR_MSG_TITLE}\n"
    "If your changes are user facing and intended to be a part of release notes, please use a label starting with `release notes:`.\n\n"  # noqa: E501  pylint: disable=line-too-long
    "If not, please add the `topic: not user facing` label.\n\n"
    "For more information, see https://github.com/pytorch/pytorch/wiki/PyTorch-AutoLabel-Bot#why-categorize-for-release-notes-and-how-does-it-work."  # noqa: E501  pylint: disable=line-too-long
)


def get_release_notes_labels() -> List[str]:
    return [label for label in get_pytorch_labels() if label.lstrip().startswith("release notes:")]


def delete_comment(comment_id: int) -> None:
    url = f"https://api.github.com/repos/pytorch/pytorch/issues/comments/{comment_id}"
    _fetch_url(url, method="DELETE")


def has_required_labels(pr: GitHubPR) -> bool:
    pr_labels = pr.get_labels()

    # Check if PR is not user facing
    is_not_user_facing_pr = any(label.strip() == "topic: not user facing" for label in pr_labels)
    if is_not_user_facing_pr:
        return True

    # Check if bot has already posted a message within the past hour to include a release notes label
    for comment in pr.get_comments():
        if comment.body_text.lstrip(" #").startswith(ERR_MSG_TITLE) and comment.author_login in BOT_AUTHORS:
            ts = datetime.strptime(comment.created_at, "%Y-%m-%dT%H:%M:%SZ")
            if (datetime.utcnow() - ts) < timedelta(hours=1):
                return True
            delete_comment(comment.database_id)
            break

    return any(label.strip() in get_release_notes_labels() for label in pr_labels)


def parse_args() -> Any:
    from argparse import ArgumentParser
    parser = ArgumentParser("Check PR labels")
    parser.add_argument("pr_num", type=int)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = GitRepo(get_git_repo_dir(), get_git_remote_name())
    org, project = repo.gh_owner_and_name()
    pr = GitHubPR(org, project, args.pr_num)

    try:
        if not has_required_labels(pr):
            print(ERR_MSG)
            gh_post_pr_comment(pr.org, pr.project, pr.pr_num, ERR_MSG)
            exit(1)
    except Exception as e:
        pass


if __name__ == "__main__":
    main()
