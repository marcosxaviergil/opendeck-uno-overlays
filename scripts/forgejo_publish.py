"""Send this folder to Forgejo as a new commit on top of the remote history, with the tag v<plugin version>.

Nothing on the remote is deleted: the existing history, tags, releases and Actions runs stay. The new
commit holds the project exactly as this folder has it (files removed here are removed in the commit).
Pushing the tag makes the workflow build the plugin and the manual and publish them as that version's
release.

If the tag already exists:
- with a release: stop, nothing changes (a published version is never replaced from here; bump the version);
- without a release (a build that failed): the tag moves to the new commit, only if its old commit is in
  the history of main, with --force-with-lease, so nothing else is overwritten.

The token comes from your git credential helper, or is asked once without echo and saved there
(scripts/forgejo_reset.py, `login`). It never goes on a command line or into a log: git receives it
through GIT_CONFIG_* environment variables. Requests carry their own User-Agent (Cloudflare error 1010).

API (Forgejo /api/v1, from the Gitea 1.21 spec Forgejo forked): GET /repos/{owner}/{repo},
GET /repos/{owner}/{repo}/releases/tags/{tag} (200 or 404).

    python3 scripts/forgejo_publish.py --server https://forgejo.example --repo owner/name
"""

import argparse
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

from forgejo_reset import Forgejo, login

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
SKIP = shutil.ignore_patterns(".git", "dist", "__pycache__", ".ruff_cache", "node_modules", "*.pyc")


def fail(message):
    sys.exit(f"publish: {message}")


def git(*args, cwd, env=None, check=True):
    """The user's own git (from PATH, with their configuration); arguments are fixed by this script."""
    result = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)  # noqa: S603, S607
    if check and result.returncode:
        fail(f"git {args[0]} failed: {result.stderr.strip()[-500:]}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Send this folder to Forgejo as a new commit with the version tag.")
    parser.add_argument("--server", required=True, help="https://forgejo.example")
    parser.add_argument("--repo", required=True, help="owner/name")
    args = parser.parse_args()
    server = args.server.rstrip("/")
    if not re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?(/[\w.-]+)*", server):
        fail("--server must look like https://forgejo.example")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        fail("--repo must look like owner/name")
    owner, name = args.repo.split("/")
    for key in ("user.name", "user.email"):
        if git("config", key, cwd=ROOT, check=False).returncode:
            fail(f'set your git identity first: git config --global {key} "..."')

    version = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))["Version"]
    tag = f"v{version}"
    subprocess.run([sys.executable, "-B", "scripts/build.py"], cwd=ROOT, check=True)  # versions, vendor, SHA256SUMS

    token, me = login(server)
    forgejo = Forgejo(server, token)
    status, answer = forgejo("GET", f"/repos/{owner}/{name}")
    if status != 200:
        fail(f"could not read {owner}/{name} (HTTP {status}): {answer}")
    status, answer = forgejo("GET", f"/repos/{owner}/{name}/releases/tags/{urllib.parse.quote(tag)}")
    if status == 200:
        fail(f"the release {tag} is already published; nothing was changed. Raise the version to publish again.")
    if status != 404:
        fail(f"could not check the release {tag} (HTTP {status}): {answer}")

    auth = base64.b64encode(f"{me['login']}:{token}".encode()).decode()
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": f"http.{server}/.extraHeader",
        "GIT_CONFIG_VALUE_0": f"Authorization: Basic {auth}",
    }
    url = f"{server}/{owner}/{name}.git"
    with tempfile.TemporaryDirectory(prefix="uno-publish-") as work:
        clone = pathlib.Path(work) / "repo"
        git("clone", "--quiet", url, str(clone), cwd=work, env=env)
        if git("rev-parse", "--verify", "--quiet", "HEAD", cwd=clone, check=False).returncode:
            git("checkout", "--quiet", "-b", "main", cwd=clone)  # an empty remote
        git("rm", "-r", "--quiet", "--ignore-unmatch", ".", cwd=clone)
        shutil.copytree(ROOT, clone, ignore=SKIP, dirs_exist_ok=True)
        git("add", "--all", cwd=clone)
        if git("diff", "--cached", "--quiet", cwd=clone, check=False).returncode:
            git("commit", "--quiet", "-m", f"UNO Overlays {version}", cwd=clone)
            print(f"New commit on top of the remote history: UNO Overlays {version}.")
        else:
            print("The remote main already has exactly this project: no new commit.")
        branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=clone).stdout.strip()

        remote_tag = git("ls-remote", "--tags", "origin", f"refs/tags/{tag}", cwd=clone, env=env).stdout.split()
        lease = []
        if remote_tag:
            old = git("rev-list", "-n", "1", remote_tag[0], cwd=clone, check=False).stdout.strip()
            if not old or git("merge-base", "--is-ancestor", old, "HEAD", cwd=clone, check=False).returncode:
                fail(f"the tag {tag} exists on a commit outside the history of {branch}; nothing was changed")
            lease = [f"--force-with-lease=refs/tags/{tag}:{remote_tag[0]}"]
            print(f"The tag {tag} has no release: it moves to the new commit.")
        git("tag", "-fa", tag, "-m", f"UNO Overlays {version}", cwd=clone)
        git("push", "--quiet", "origin", f"HEAD:refs/heads/{branch}", cwd=clone, env=env)
        git("push", "--quiet", *lease, "origin", f"refs/tags/{tag}", cwd=clone, env=env)
    print(
        f"\nPushed {branch} and {tag}; nothing was deleted. The workflow now tests, builds and publishes:\n"
        f"  Actions:  {server}/{owner}/{name}/actions\n  Releases: {server}/{owner}/{name}/releases"
    )


if __name__ == "__main__":
    main()
