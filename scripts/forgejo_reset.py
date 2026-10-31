"""Replace a Forgejo repository with this folder: one commit on main and the tag v<plugin version>.

Everything on the remote goes: the repository is deleted (commits, branches, tags, releases, Actions
runs and logs, issues, repository secrets and runners registered only there) and created again with
the same visibility and description, with Actions and releases on. Pushing the tag makes the
workflow build the plugin and publish it as that version's release. Before deleting, a mirror of the
old repository is saved next to this folder.

The token comes from your git credential helper (`git credential fill`, the same place `git push`
looks). When none is saved there, or the saved one is refused, it is asked once without echo and then
handed to the helper (`git credential approve`), so the next run does not ask again. It never goes on
a command line or into a log: git receives it through GIT_CONFIG_* environment variables. Token
scopes: write:repository and write:user (write:organization too when the owner is an organization).

Requests carry their own User-Agent: a Cloudflare in front of Forgejo can refuse Python's default
one with 403 (error 1010, "blocked access based on your browser's signature").

API (Forgejo /api/v1, from the Gitea 1.21 spec Forgejo forked): GET /user, GET/DELETE/PATCH
/repos/{owner}/{repo}, POST /user/repos or /orgs/{org}/repos. Git over HTTPS accepts an access
token as the Basic auth password.

    python3 scripts/forgejo_reset.py --server https://forgejo.example --repo owner/name
"""

import argparse
import base64
import getpass
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
USER_AGENT = "opendeck-uno-overlays"  # Cloudflare refuses Python's default one (error 1010)


def fail(message):
    sys.exit(f"reset: {message}")


class Forgejo:
    """The Forgejo API (/api/v1) with a token; also used by forgejo_release.py and forgejo_publish.py."""

    def __init__(self, server, token):
        self.api, self.token = server.rstrip("/") + "/api/v1", token

    def __call__(self, method, path, body=None, kind="application/json"):
        """(HTTP status, answer). A dict or list body goes as JSON; bytes go as they are, with `kind`."""
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        headers = {"Authorization": f"token {self.token}", "Accept": "application/json", "User-Agent": USER_AGENT}
        if data:
            headers["Content-Type"] = kind
        req = urllib.request.Request(self.api + path, data, headers, method=method)  # noqa: S310 - checked in main()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(2000).decode("utf-8", "replace")


def git(*args, env=None, check=True, **options):
    """The user's own git (from PATH, with their configuration); arguments are fixed by this script."""
    return subprocess.run(["git", *args], cwd=ROOT, env=env, check=check, capture_output=not check, **options)  # noqa: S603, S607


def credential(server, action, fields=""):
    """Ask the user's git credential helper; git never prompts here (GIT_TERMINAL_PROMPT=0)."""
    url = urllib.parse.urlsplit(server)
    query = f"protocol={url.scheme}\nhost={url.netloc}\n{fields}\n"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}
    result = git("credential", action, env=env, check=False, input=query, text=True)
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def login(server):
    """(token, user) from the credential helper, or asked once and saved there."""
    token = credential(server, "fill").get("password", "")
    if token:
        status, me = Forgejo(server, token)("GET", "/user")
        if status == 200:
            print("Using the Forgejo token saved in your git credential helper.")
            return token, me
        print(f"The saved credential was refused (HTTP {status}); a token is needed.")
    token = getpass.getpass("Forgejo token (write:repository, write:user): ").strip()
    status, me = Forgejo(server, token)("GET", "/user")
    if status != 200:
        fail(f"the token was refused (HTTP {status}): {me}")
    credential(server, "approve", f"username={me['login']}\npassword={token}\n")
    print("Token saved in your git credential helper for the next runs.")
    return token, me


def main():
    parser = argparse.ArgumentParser(description="Replace a Forgejo repository with this folder.")
    parser.add_argument("--server", required=True, help="https://forgejo.example")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--git-url", help="push URL (default: <server>/<owner>/<name>.git)")
    args = parser.parse_args()
    server = args.server.rstrip("/")
    if not re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?(/[\w.-]+)*", server):
        fail("--server must look like https://forgejo.example")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        fail("--repo must look like owner/name")
    owner, name = args.repo.split("/")
    git_url = args.git_url or f"{server}/{owner}/{name}.git"
    if (ROOT / ".git").exists():
        fail(f"{ROOT} already has a .git folder: run this in a fresh copy of the project")
    for key in ("user.name", "user.email"):
        if git("config", key, check=False).returncode:
            fail(f'set your git identity first: git config --global {key} "..."')

    version = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))["Version"]
    tag = f"v{version}"
    subprocess.run([sys.executable, "-B", "scripts/build.py"], cwd=ROOT, check=True)  # versions, vendor, SHA256SUMS

    token, me = login(server)
    forgejo = Forgejo(server, token)
    status, old = forgejo("GET", f"/repos/{owner}/{name}")
    if status not in (200, 404):
        fail(f"could not read {owner}/{name} (HTTP {status}): {old}")
    exists = status == 200
    private = bool(old["private"]) if exists else True
    description = old.get("description", "") if exists else "UNO Overlays for OpenDeck (Linux)"

    print(f"\n{server}/{owner}/{name}", "exists" if exists else "does not exist yet")
    if exists:
        print(
            "DELETING it removes for good: commits, branches, tags, releases and their files, Actions runs\n"
            "and logs, issues, pull requests, wiki, repository secrets and runners registered only there."
        )
    print(f"Then: new repository ({'private' if private else 'public'}), one commit on main, tag {tag}.")
    if input(f"Type {name} to continue: ").strip() != name:
        fail("cancelled; nothing was changed")

    auth = base64.b64encode(f"{me['login']}:{token}".encode()).decode()
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"http.{server}/.extraHeader",
        "GIT_CONFIG_VALUE_0": f"Authorization: Basic {auth}",
    }
    if exists:
        backup = ROOT.parent / f"{name}-backup-{time.strftime('%Y%m%d-%H%M%S')}.git"
        git("clone", "--quiet", "--mirror", git_url, str(backup), env=env)
        print(f"Old repository saved in {backup}")
        status, answer = forgejo("DELETE", f"/repos/{owner}/{name}")
        if status != 204:
            fail(f"could not delete {owner}/{name} (HTTP {status}): {answer}")
        print("Remote repository deleted.")

    create = {"name": name, "private": private, "description": description, "default_branch": "main"}
    path = "/user/repos" if owner == me["login"] else f"/orgs/{owner}/repos"
    status, answer = forgejo("POST", path, create)
    if status != 201:
        fail(f"could not create {owner}/{name} (HTTP {status}): {answer}")
    status, answer = forgejo("PATCH", f"/repos/{owner}/{name}", {"has_actions": True, "has_releases": True})
    if status != 200:
        fail(f"could not turn on Actions and releases (HTTP {status}): {answer}")
    print("Remote repository created with Actions and releases on.")

    git("init", "--quiet", "-b", "main")
    git("add", "--all")
    git("commit", "--quiet", "-m", f"UNO Overlays {version}")
    git("tag", "-a", tag, "-m", f"UNO Overlays {version}")
    git("remote", "add", "origin", git_url)
    git("push", "--quiet", "origin", "main", tag, env=env)
    print(
        f"\nPushed main and {tag}. The workflow now tests, builds and publishes the release:\n"
        f"  Actions:  {server}/{owner}/{name}/actions\n  Releases: {server}/{owner}/{name}/releases"
    )


if __name__ == "__main__":
    main()
