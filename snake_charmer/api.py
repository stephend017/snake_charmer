import re
from github import Commit
from snake_charmer.models import VersionType
from snake_charmer.github_api import GithubAPI
from github.PullRequest import PullRequest
from github.Label import Label


class API:
    """
    Object to manage the different operations
    of this program
    """

    @staticmethod
    def on_pull_request_opened(
        github_api: GithubAPI, pull_request: PullRequest
    ):
        """
        Function that runs when a pull request is opened
        This is triggered by the action

        Args:
            github_api (GithubAPI): Wrapper object for interfacing
                with github
            pull_request (PullRequest): Full PR object from
                github API
        """
        github_api.setup_labels()

    @staticmethod
    def on_pull_request_labeled(
        github_api: GithubAPI, pull_request: PullRequest, label: Label
    ):
        """
        Function that runs when a pull request has a label
        added

        Args:
            github_api (GithubAPI): Wrapper object for interfacing
                with github
            pull_request (PullRequest): Full PR object from
                github API
            label (Label): the label that was added to the pull request
        """
        labels = ["major-release", "minor-release", "revision-release"]
        labels.remove(label["name"])
        for label in pull_request["labels"]:
            if label in labels:
                # A release label that is not the one added
                # already exists. remove this label, update
                # setup.py

                # this is complicated because if we remove
                # a higher release for a lower one (minor
                # for major) the state is not recoverable
                # from the version itself (its not easy to
                # go from 0.1.0 to 0.0.7). We can fix this
                # by accessing the last commit where the
                # version was bumped from (since it
                # was committed)

                repo = github_api.get_repo()
                commits = repo.get_commits()
                index = 0
                while index < commits.totalCount:
                    commit: Commit = commits[index]

                    match = re.search(
                        r"Updated version to \d\.\d\.\d",
                        commit.commit.message,
                    )
                    if match:
                        commit_message = match.group()
                        version = commit_message[19:]
                        github_api._setup_py.replace(
                            github_api._get_setup_py_version()[1:-1], version
                        )
                        break
                    index += 1

                repo.get_pull(pull_request["number"]).remove_from_labels(label)

        github_api.load_setup_py_file(pull_request["head"]["ref"])
        github_api.update_setup_py_file(VersionType.from_label(label["name"]))
        github_api.push_setup_py_file(pull_request["number"])

    @staticmethod
    def on_pull_request_unlabeled(
        github_api: GithubAPI, pull_request: PullRequest, label: Label
    ):
        """
        Function that runs when a pull request has a label
        removed

        Args:
            github_api (GithubAPI): Wrapper object for interfacing
                with github
            pull_request (PullRequest): Full PR object from
                github API
            label (Label): the label that was removed to the pull request
        """
        github_api.load_setup_py_file(pull_request["head"]["ref"])
        github_api.update_setup_py_file(
            VersionType.from_label(label["name"]), increment=False
        )
        github_api.push_setup_py_file(pull_request["number"])

    @staticmethod
    def on_pull_request_merged(
        github_api: GithubAPI, pull_request: PullRequest
    ):
        """
        Function that runs when a pull request is merged

        Args:
            github_api (GithubAPI): Wrapper object for interfacing
                with github
            pull_request (PullRequest): Full PR object from
                github API
        """
        # generate changelog
        # create release
        defined_labels = ["major-release", "minor-release", "revision-release"]
        labels = pull_request["labels"]

        for label in labels:
            if label["name"] in defined_labels:
                github_api.create_release("main")
                return
