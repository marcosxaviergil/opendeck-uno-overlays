"""GitHub release script against a local stand-in of the GitHub REST API (releases, release assets, git refs).

The stand-in answers like the documented endpoints and, like a repository with immutable releases on,
refuses an asset upload to a published release (422): files are attached to a draft, which is then
published. It is not GitHub.
"""

import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse

from support import ROOT

TOKEN = "t0ken-for-tests"
VERSION = json.loads((ROOT / "plugin/dev.br.consciencia.opendeck.uno-overlays.sdPlugin/manifest.json").read_text())[
    "Version"
]
TAG = f"v{VERSION}"


class FakeGitHub(http.server.ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.calls, self.next_id = [], 100
        self.refs = {}  # tag -> (object type, sha) of /git/ref/tags/{tag}
        self.tag_objects = {}  # annotated tag sha -> (object type, sha) it points to (/git/tags/{sha})
        self.releases = {5: {"tag_name": "v1.0.0", "draft": False, "assets": []}}
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def answer(self, status, body=None):
        data = json.dumps(body).encode() if body is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def release_view(self, number):
        release = self.server.releases[number]
        upload = f"{self.server.url}/uploads/repos/owner/name/releases/{number}/assets{{?name,label}}"
        assets = [{"name": asset["name"]} for asset in release["assets"]]
        return {
            "id": number,
            **release,
            "assets": assets,
            "upload_url": upload,
            "html_url": f"{self.server.url}/releases/{number}",
        }

    def handle_any(self):
        f = self.server
        url = urllib.parse.urlsplit(self.path)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        f.calls.append((self.command, url.path, self.headers.get("Authorization")))
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self.answer(401, {"message": "Bad credentials"})
        parts = url.path.strip("/").split("/")
        uploads = parts[0] == "uploads"
        if uploads:
            parts = parts[1:]
        if parts[:3] != ["repos", "owner", "name"]:
            return self.answer(404, {"message": "Not Found"})
        rest = parts[3:]
        if rest[:3] == ["git", "ref", "tags"] and self.command == "GET":
            found = f.refs.get(rest[3])
            if not found:
                return self.answer(404, {"message": "Not Found"})
            return self.answer(200, {"ref": f"refs/tags/{rest[3]}", "object": {"type": found[0], "sha": found[1]}})
        if rest[:2] == ["git", "tags"] and self.command == "GET":
            found = f.tag_objects.get(rest[2])
            if not found:
                return self.answer(404, {"message": "Not Found"})
            return self.answer(200, {"sha": rest[2], "object": {"type": found[0], "sha": found[1]}})
        if rest == ["releases"] and self.command == "GET":
            return self.answer(200, [self.release_view(n) for n in sorted(f.releases, reverse=True)])
        if rest == ["releases"] and self.command == "POST":
            data = json.loads(body)
            f.next_id += 1
            f.releases[f.next_id] = {**data, "assets": []}
            return self.answer(201, self.release_view(f.next_id))
        if len(rest) == 2 and rest[0] == "releases" and int(rest[1]) in f.releases:
            number = int(rest[1])
            if self.command == "DELETE":
                del f.releases[number]  # the git tag stays, as on GitHub
                return self.answer(204)
            if self.command == "PATCH":
                f.releases[number].update(json.loads(body))
                return self.answer(200, self.release_view(number))
        if uploads and len(rest) == 3 and rest[0] == "releases" and rest[2] == "assets" and self.command == "POST":
            release = f.releases[int(rest[1])]
            if not release["draft"]:
                return self.answer(422, {"message": "Cannot upload assets to an immutable release."})
            name = urllib.parse.parse_qs(url.query)["name"][0]
            release["assets"].append({"name": name, "type": self.headers["Content-Type"], "data": body})
            return self.answer(201, {"browser_download_url": f"{f.url}/download/{name}"})
        return self.answer(404, {"message": "Not Found"})

    do_GET = do_POST = do_DELETE = do_PATCH = handle_any


class Release(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.github = FakeGitHub()
        self.addCleanup(self.github.server_close)
        self.addCleanup(self.github.shutdown)
        self.project = self.work / "project"
        ignore = shutil.ignore_patterns(".git", "dist", "__pycache__", ".ruff_cache", "node_modules")
        shutil.copytree(ROOT, self.project, ignore=ignore)
        self.env = {
            "GITHUB_API_URL": self.github.url,
            "GITHUB_REPOSITORY": "owner/name",
            "GITHUB_REF_NAME": TAG,
            "GITHUB_TOKEN": TOKEN,
            "BUILD_COMMIT": "c0ffee",
        }

    def release(self, env=None):
        return subprocess.run(
            [sys.executable, "-B", "scripts/github_release.py"],
            cwd=self.project,
            text=True,
            capture_output=True,
            env={"PATH": os.environ["PATH"], **self.env, **(env or {})},
            timeout=120,
        )

    def build(self):
        subprocess.run([sys.executable, "-B", "scripts/build.py"], cwd=self.project, check=True, capture_output=True)
        manual = self.project / "dist" / f"UNO-Overlays-{VERSION}-Manual.pdf"
        manual.write_bytes(b"%PDF-1.7 test")  # scripts/build_manual.py has its own test (test_manual)
        return self.project / "dist" / f"opendeck-uno-overlays-{VERSION}-linux.plugin.zip", manual

    def mine(self):
        return [r for r in self.github.releases.values() if r["tag_name"] == TAG]

    def test_replaces_the_same_version_attaching_both_files_to_a_draft_then_publishing(self):
        zip_file, manual = self.build()
        self.github.refs[TAG] = ("tag", "a1b2c3")  # annotated tag (git tag -a): followed to its commit
        self.github.tag_objects["a1b2c3"] = ("commit", "c0ffee")
        self.github.releases[7] = {"tag_name": TAG, "draft": False, "assets": [{"name": "old.zip"}]}
        self.github.releases[8] = {"tag_name": TAG, "draft": True, "assets": []}  # left by a failed run

        for _ in range(2):
            result = self.release()
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        (release,) = self.mine()
        self.assertEqual((release["draft"], release["prerelease"]), (False, False), "published at the end")
        self.assertEqual(release["name"], f"UNO Overlays {VERSION}")
        self.assertIn("Gatilhos", release["body"], "notes come from the CHANGELOG")
        self.assertIn(manual.name, release["body"], "the SHA-256 of both files is in the notes")
        self.assertEqual(
            release["assets"],
            [
                {"name": zip_file.name, "type": "application/zip", "data": zip_file.read_bytes()},
                {"name": manual.name, "type": "application/pdf", "data": manual.read_bytes()},
            ],
        )
        self.assertIn(5, self.github.releases, "releases of other versions stay")
        self.assertTrue(all(auth == f"Bearer {TOKEN}" for _, _, auth in self.github.calls))
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

        self.github.tag_objects["a1b2c3"] = ("commit", "newer")  # the tag moved: a newer run builds it
        before = json.dumps(self.github.releases, default=str)
        result = self.release()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Nothing published", result.stdout)
        self.assertEqual(before, json.dumps(self.github.releases, default=str), "untouched")

    def test_a_lightweight_tag_is_its_commit_and_a_tag_of_a_tag_is_refused(self):
        self.build()
        self.github.refs[TAG] = ("tag", "a1b2c3")
        self.github.tag_objects["a1b2c3"] = ("tag", "d4e5f6")
        result = self.release()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not read the commit", result.stderr)
        self.assertEqual(self.mine(), [], "nothing published for a tag that does not name a commit")

        self.github.refs[TAG] = ("commit", "c0ffee")
        result = self.release()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(len(self.mine()), 1)

    def test_refuses_a_tag_that_is_not_the_version_missing_files_or_settings(self):
        result = self.release({"GITHUB_REF_NAME": "v9.9.9"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match the plugin version", result.stderr)

        result = self.release()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is missing", result.stderr, "nothing is published before both files exist")

        result = self.release({"GITHUB_TOKEN": ""})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub Actions", result.stderr)

        for url in ("file:///etc", "http://api.github.example"):  # the token never travels without TLS
            result = self.release({"GITHUB_API_URL": url})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must be https", result.stderr)
        self.assertEqual(self.github.calls, [], "no request before every check passes")


if __name__ == "__main__":
    unittest.main()
