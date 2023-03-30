import os
from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)

app_id = '311893'

# Read the bot certificate
with open(
        "./umons-bot-virgil.2023-03-30.private-key.pem",
        'r'
) as cert_file:
    app_key = cert_file.read()

# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)


def issue_opened_event(repo, payload):
    issue = repo.get_issue(number=payload['issue']['number'])
    author = issue.user.login

    issue.add_to_labels("pending", "needs triage")

    response = f"Thanks for opening this issue, @{author}! " \
               f"The repository maintainers will look into it ASAP! :speech_balloon:"
    issue.create_comment(f"{response}")


def pull_request_opened_event(repo, payload):
    # say thanks when a pull request has been closed
    pr = repo.get_pull(number=payload['pull_request']['number'])
    author = pr.user.login

    response = f"Thanks , {author}! "

    pr.create_issue_comment(f"{response}")
    # delete the branch that was merged
    repo.get_git_ref(f"heads/{pr.head.ref}").delete()


def prevent_merge_for_wip_pr(repo, payload):
    pull_request = repo.get_pull(number=payload['pull_request']['number'])
    author = pull_request.user.login
    title = pull_request.title.lower()
    if 'wip' in title or 'work in progress' in title or "do not merge" in title:
        repo.get_commit(sha=pull_request.head.sha).create_status(state="pending", description="Work in progress",
                                                                 context="WIP")
        response = f"Thanks for your contribution, @{author}! " \
                   f"Your pull request is still a work in progress. " \
                   f"Please remove the WIP tag from the title when you are ready to merge. :construction:"
        pull_request.create_issue_comment(f"{response}")
    else:
        repo.get_commit(sha=pull_request.head.sha).create_status(state="success", description="Ready to merge",
                                                                 context="WIP")
        response = f"Thanks for your contribution, @{author}! " \
                   f"Your pull request is ready to be mered. :rocket:"
        pull_request.create_issue_comment(f"{response}")
@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub issue creation event
    if all(k in payload.keys() for k in ['action', 'issue']) and payload['action'] == 'opened':
        issue_opened_event(repo, payload)
    elif all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        pull_request_opened_event(repo, payload)
    elif all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'edited':
        pull_request_opened_event(repo, payload)
    return "", 204


if __name__ == "__main__":
    app.run(debug=True, port=5000)
