"""Publish the built plugin and its manual as the Forgejo release of the pushed version tag (Actions step).

Same version again: the earlier release of that tag and its files are deleted first, so only the
newest build remains. The git tag itself is kept. The ZIP and the PDF must already be in dist/
(scripts/build.py, scripts/build_manual.py). With BUILD_COMMIT (the commit the run built), nothing is
published when the tag already points elsewhere: a moved tag never gets an older build.

API (Forgejo /api/v1; paths from the Forgejo release docs and the Gitea 1.21 spec Forgejo forked):
DELETE /repos/{owner}/{repo}/releases/tags/{tag} (204, or 404 when there is none),
POST /repos/{owner}/{repo}/releases (201), POST .../releases/{id}/assets, multipart field "attachment",
GET /repos/{owner}/{repo}/tags/{tag} (commit.sha: the commit the tag points to).
Auth: the job's automatic token (FORGEJO_TOKEN or GITHUB_TOKEN), which can write to its own repository.
Requests carry their own User-Agent: a Cloudflare in front of Forgejo can refuse Python's default one
with 403 (error 1010).

    python3 -B scripts/forgejo_release.py   # env: GITHUB_SERVER_URL, GITHUB_REPOSITORY, GITHUB_REF_NAME, FORGEJO_TOKEN
"""

import hashlib
import json
import os
import pathlib
import re
import secrets
import sys
import urllib.parse

from forgejo_reset import Forgejo

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"


def fail(message):
    sys.exit(f"release: {message}")


def notes(version):
    """The CHANGELOG section of this version (Keep a Changelog)."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(rf"^## \[{re.escape(version)}\].*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1).strip() if match else ""


def multipart(name, data, kind):
    boundary = secrets.token_hex(16)
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="attachment"; filename="{name}"\r\n'
        f"Content-Type: {kind}\r\n\r\n"
    )
    return head.encode() + data + f"\r\n--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def main():
    env = os.environ
    token = env.get("FORGEJO_TOKEN") or env.get("GITHUB_TOKEN")
    server, repository, tag = env.get("GITHUB_SERVER_URL"), env.get("GITHUB_REPOSITORY"), env.get("GITHUB_REF_NAME")
    if not (token and server and repository and tag):
        fail("run it in Forgejo Actions: token, server, repository or tag is missing")
    if not server.startswith(("https://", "http://")):
        fail("GITHUB_SERVER_URL must be an http(s) URL")
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
    request = Forgejo(server, token)
    base = f"/repos/{repository}"
    api = f"{base}/releases"

    # A tag moved to a newer commit starts a newer build: an older run that ends later never replaces it.
    built = env.get("BUILD_COMMIT")
    if built:
        status, answer = request("GET", f"{base}/tags/{urllib.parse.quote(tag)}")
        if status != 200:
            fail(f"could not read the {tag} tag (HTTP {status}): {answer}")
        if (answer.get("commit") or {}).get("sha") != built:
            print(f"{tag} now points to another commit; its own run publishes the release. Nothing published here.")
            return

    status, answer = request("DELETE", f"{api}/tags/{urllib.parse.quote(tag)}")
    if status not in (204, 404):
        fail(f"could not delete the earlier {tag} release (HTTP {status}): {answer}")
    print(f"Earlier {tag} release deleted." if status == 204 else f"No earlier {tag} release.")

    sums = "\n".join(f"| `{path.name}` | `{hashlib.sha256(path.read_bytes()).hexdigest()}` |" for path, _ in files)
    body = f"{notes(version)}\n\n| Arquivo | SHA-256 |\n| --- | --- |\n{sums}".strip()
    release = {"tag_name": tag, "name": f"UNO Overlays {version}", "body": body, "draft": False, "prerelease": False}
    status, answer = request("POST", api, release)
    if status != 201:
        fail(f"could not create the {tag} release (HTTP {status}): {answer}")
    print(f"Release {tag}: {answer.get('html_url', '')}")
    for path, kind in files:
        upload, form = multipart(path.name, path.read_bytes(), kind)
        status, asset = request("POST", f"{api}/{answer['id']}/assets?name={path.name}", upload, form)
        if status != 201:
            fail(f"could not attach {path.name} (HTTP {status}): {asset}")
        print(f"File: {asset.get('browser_download_url', path.name)}")


if __name__ == "__main__":
    main()
