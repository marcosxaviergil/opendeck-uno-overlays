"""Publish the built plugin and its manual as the GitHub release of the pushed version tag (Actions step).

The GitHub counterpart of forgejo_release.py, with the same rules: the tag must be v<plugin version>,
the ZIP and the PDF must already be in dist/ (scripts/build.py, scripts/build_manual.py), the notes are
the CHANGELOG section of the version plus the SHA-256 of both files, and the same version again
replaces its earlier release (the git tag itself is kept). With BUILD_COMMIT (the commit the run
built), nothing is published when the tag already points elsewhere: a moved tag never gets an older
build.

The release is created as a draft, gets its two files and is published last: with immutable releases
on, GitHub refuses files added after publishing, and a run that fails halfway leaves a draft instead of
a public release without its files. The next run of the same version deletes that draft.

API (GitHub REST, docs.github.com/rest: releases, release assets, git references, git tags):
GET /repos/{owner}/{repo}/git/ref/tags/{tag} (object: the commit, or an annotated tag that
GET /repos/{owner}/{repo}/git/tags/{sha} follows to its commit), GET /repos/{owner}/{repo}/releases
(drafts are listed for a token that can push), DELETE /repos/{owner}/{repo}/releases/{id} (204),
POST /repos/{owner}/{repo}/releases (201), POST to the release's upload_url with ?name= and the raw
file as the body (201), PATCH /repos/{owner}/{repo}/releases/{id} (200).
Auth: the job's GITHUB_TOKEN, which the workflow passes in env with `permissions: contents: write`.

    python3 -B scripts/github_release.py   # env: GITHUB_API_URL, GITHUB_REPOSITORY, GITHUB_REF_NAME, GITHUB_TOKEN
"""

import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from forgejo_release import PLUGIN, ROOT, notes
from forgejo_reset import USER_AGENT

API_VERSION = "2022-11-28"  # X-GitHub-Api-Version
LOOPBACK = ("127.0.0.1", "localhost", "::1")  # plain http only here (the tests' stand-in); the token needs TLS


def fail(message):
    sys.exit(f"release: {message}")


def is_safe(url):
    """https, or http to this machine only: the token goes in every request."""
    parts = urllib.parse.urlsplit(url)
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOOPBACK)


class GitHub:
    """The GitHub REST API with a token. Paths are relative to the API; an upload URL is absolute."""

    def __init__(self, api, token):
        self.api, self.token = api.rstrip("/"), token

    def __call__(self, method, path, body=None, kind="application/json"):
        """(HTTP status, answer). A dict body goes as JSON; bytes go as they are, with `kind`."""
        url = path if path.startswith(("https://", "http://")) else self.api + path
        data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        }
        if data:
            headers["Content-Type"] = kind
        req = urllib.request.Request(url, data, headers, method=method)  # noqa: S310 - is_safe() checked by the callers
        try:
            with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(2000).decode("utf-8", "replace")


def tag_commit(request, base, tag):
    """The commit a tag points to; an annotated tag (git tag -a) is followed to its commit."""
    status, answer = request("GET", f"{base}/git/ref/tags/{urllib.parse.quote(tag)}")
    target = answer.get("object") if status == 200 else None
    if target and target.get("type") == "tag":
        status, answer = request("GET", f"{base}/git/tags/{urllib.parse.quote(str(target.get('sha')))}")
        target = answer.get("object") if status == 200 else None
    if not target or target.get("type") != "commit":
        fail(f"could not read the commit of the {tag} tag (HTTP {status}): {answer}")
    return target.get("sha")


def main():
    env = os.environ
    token, api = env.get("GITHUB_TOKEN"), env.get("GITHUB_API_URL")
    repository, tag = env.get("GITHUB_REPOSITORY"), env.get("GITHUB_REF_NAME")
    if not (token and api and repository and tag):
        fail("run it in GitHub Actions with GITHUB_TOKEN in env: token, API URL, repository or tag is missing")
    if not is_safe(api):
        fail("GITHUB_API_URL must be https (http only for localhost)")
    version = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))["Version"]
    if tag != f"v{version}":
        fail(f"tag {tag} does not match the plugin version {version}: tag the commit v{version}")
    files = [  # (path, media type): the plugin and its manual, one release, one build
        (ROOT / "dist" / f"opendeck-uno-overlays-{version}-linux.plugin.zip", "application/zip"),
        (ROOT / "dist" / f"UNO-Overlays-{version}-Manual.pdf", "application/pdf"),
    ]
    for path, _ in files:
        if not path.is_file():
            fail(f"{path.relative_to(ROOT)} is missing: run scripts/build.py and scripts/build_manual.py first")
    request = GitHub(api, token)
    base = f"/repos/{repository}"

    # A tag moved to a newer commit starts a newer build: an older run that ends later never replaces it.
    built = env.get("BUILD_COMMIT")
    if built and tag_commit(request, base, tag) != built:
        print(f"{tag} now points to another commit; its own run publishes the release. Nothing published here.")
        return

    # Only the first page is read (up to 100 releases).
    status, releases = request("GET", f"{base}/releases?per_page=100")
    if status != 200:
        fail(f"could not list the releases (HTTP {status}): {releases}")
    earlier = [old for old in releases if old.get("tag_name") == tag]
    for old in earlier:
        status, answer = request("DELETE", f"{base}/releases/{old['id']}")
        if status not in (204, 404):
            fail(f"could not delete the earlier {tag} release (HTTP {status}): {answer}")
        print(f"Earlier {tag} {'draft' if old.get('draft') else 'release'} deleted.")
    if not earlier:
        print(f"No earlier {tag} release.")

    sums = "\n".join(f"| `{path.name}` | `{hashlib.sha256(path.read_bytes()).hexdigest()}` |" for path, _ in files)
    body = f"{notes(version)}\n\n| Arquivo | SHA-256 |\n| --- | --- |\n{sums}".strip()
    draft = {"tag_name": tag, "name": f"UNO Overlays {version}", "body": body, "draft": True, "prerelease": False}
    status, release = request("POST", f"{base}/releases", draft)
    if status != 201:
        fail(f"could not create the {tag} draft (HTTP {status}): {release}")
    upload = str(release.get("upload_url") or "").split("{", 1)[0]  # hypermedia template: ...assets{?name,label}
    if not is_safe(upload):
        fail(f"the upload URL of the {tag} draft must be https (http only for localhost)")
    for path, kind in files:
        name = urllib.parse.quote(path.name)
        status, asset = request("POST", f"{upload}?name={name}", path.read_bytes(), kind)
        if status != 201:
            fail(f"could not attach {path.name} (HTTP {status}): {asset}. The draft stays until the next run.")
        print(f"File: {asset.get('browser_download_url', path.name)}")
    status, answer = request("PATCH", f"{base}/releases/{release['id']}", {"draft": False})
    if status != 200:
        fail(f"could not publish the {tag} draft (HTTP {status}): {answer}")
    print(f"Release {tag}: {answer.get('html_url', '')}")


if __name__ == "__main__":
    main()
