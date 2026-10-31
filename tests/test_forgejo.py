"""Forgejo publishing scripts against a local stand-in of Forgejo (API paths of the Gitea 1.21 spec).

The stand-in answers like the documented endpoints and serves git over HTTP with `git http-backend`,
accepting pushes only with the access token as the Basic auth password. Like the Cloudflare in front
of forgejo.consciencia.dev.br (error 1010), it refuses Python's default User-Agent. It is not Forgejo.
"""

import base64
import email.parser
import email.policy
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


class FakeForgejo(http.server.ThreadingHTTPServer):
    def __init__(self, git_root):
        super().__init__(("127.0.0.1", 0), Handler)
        self.git_root = git_root
        self.repos = {"owner/name": {"private": True, "description": "old", "releases": {7: {"tag": "v1.0.0"}}}}
        self.bare("name")
        self.calls, self.next_id, self.tags = [], 100, {}  # tag -> commit it points to (API tags/{tag})
        threading.Thread(target=self.serve_forever, daemon=True).start()

    def bare(self, name):
        path = self.git_root / "owner" / f"{name}.git"
        subprocess.run(["git", "init", "--quiet", "--bare", "-b", "main", str(path)], check=True)
        return path

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

    def read_body(self):
        if self.headers.get("Transfer-Encoding") != "chunked":
            return self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = b""
        while size := int(self.rfile.readline().split(b";")[0], 16):
            body += self.rfile.read(size)
            self.rfile.readline()
        self.rfile.readline()
        return body

    def git_http(self, url, body):
        """git http-backend (CGI); a push needs the token as the Basic auth password, like Forgejo."""
        expected = "Basic " + base64.b64encode(f"owner:{TOKEN}".encode()).decode()
        if self.headers.get("Authorization") != expected:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Forgejo"')
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        env = {
            "PATH": os.environ["PATH"],
            "GIT_PROJECT_ROOT": str(self.server.git_root),
            "GIT_HTTP_EXPORT_ALL": "1",
            "PATH_INFO": url.path,
            "QUERY_STRING": url.query,
            "REQUEST_METHOD": self.command,
            "REMOTE_USER": "owner",
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "HTTP_CONTENT_ENCODING": self.headers.get("Content-Encoding", ""),
        }
        out = subprocess.run(["git", "http-backend"], input=body, env=env, capture_output=True, check=True).stdout
        head, _, content = out.partition(b"\r\n\r\n")
        headers = dict(line.split(": ", 1) for line in head.decode().split("\r\n") if line)
        self.send_response(int(headers.pop("Status", "200").split()[0]))
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_any(self):
        f = self.server
        url = urllib.parse.urlsplit(self.path)
        body = self.read_body()
        if self.headers.get("User-Agent", "").startswith("Python-urllib"):
            return self.answer(403, {"title": "Error 1010: Access denied", "error_code": 1010})
        if ".git/" in url.path:
            return self.git_http(url, body)
        f.calls.append((self.command, url.path, self.headers.get("Authorization")))
        if self.headers.get("Authorization") != f"token {TOKEN}":
            return self.answer(401, {"message": "token"})
        parts = url.path.removeprefix("/api/v1").strip("/").split("/")
        if parts == ["user"]:
            return self.answer(200, {"login": "owner"})
        if parts == ["user", "repos"] and self.command == "POST":
            data = json.loads(body)
            f.repos["owner/" + data["name"]] = {**data, "releases": {}}
            f.bare(data["name"])
            return self.answer(201, {"full_name": "owner/" + data["name"]})
        if parts[0] != "repos" or len(parts) < 3:
            return self.answer(404, {"message": "not found"})
        repo = f.repos.get(f"{parts[1]}/{parts[2]}")
        rest = parts[3:]
        if repo is None:
            return self.answer(404, {"message": "not found"})
        if not rest:
            if self.command == "GET":
                return self.answer(200, {k: v for k, v in repo.items() if k != "releases"})
            if self.command == "DELETE":
                del f.repos[f"{parts[1]}/{parts[2]}"]
                shutil.rmtree(f.git_root / parts[1] / f"{parts[2]}.git")
                return self.answer(204)
            if self.command == "PATCH":
                repo.update(json.loads(body))
                return self.answer(200, {})
        releases = repo["releases"]
        if rest[:1] == ["tags"] and self.command == "GET":
            sha = f.tags.get(rest[1])
            return self.answer(200, {"name": rest[1], "commit": {"sha": sha}}) if sha else self.answer(404, {})
        if rest[:2] == ["releases", "tags"] and self.command == "GET":
            found = [r for r in releases.values() if r["tag"] == rest[2]]
            return self.answer(200, {"tag_name": rest[2]}) if found else self.answer(404, {"message": "not found"})
        if rest[:2] == ["releases", "tags"] and self.command == "DELETE":
            found = [i for i, r in releases.items() if r["tag"] == rest[2]]
            for i in found:
                del releases[i]
            return self.answer(204 if found else 404, None if found else {"message": "not found"})
        if rest == ["releases"] and self.command == "POST":
            data = json.loads(body)
            f.next_id += 1
            releases[f.next_id] = {"tag": data["tag_name"], "data": data, "assets": []}
            return self.answer(
                201, {"id": f.next_id, "html_url": f"{f.url}/owner/name/releases/tag/{data['tag_name']}"}
            )
        if len(rest) == 3 and rest[0] == "releases" and rest[2] == "assets" and self.command == "POST":
            message = email.parser.BytesParser(policy=email.policy.default).parsebytes(
                b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + body
            )
            part = next(iter(message.iter_parts()))
            releases[int(rest[1])]["assets"].append(
                {
                    "field": part.get_param("name", header="content-disposition"),
                    "name": urllib.parse.parse_qs(url.query)["name"][0],
                    "data": part.get_payload(decode=True),
                }
            )
            return self.answer(201, {"browser_download_url": f.url + "/file"})
        return self.answer(404, {"message": "not found"})

    do_GET = do_POST = do_DELETE = do_PATCH = handle_any


class Scripts(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.forgejo = FakeForgejo(self.work / "server")
        self.addCleanup(self.forgejo.server_close)
        self.addCleanup(self.forgejo.shutdown)
        self.project = self.work / "project"
        ignore = shutil.ignore_patterns(".git", "dist", "__pycache__", ".ruff_cache", "node_modules")
        shutil.copytree(ROOT, self.project, ignore=ignore)
        gitconfig = self.work / "gitconfig"
        self.credentials = self.work / "git-credentials"
        gitconfig.write_text(
            "[user]\n\tname = Tester\n\temail = tester@example.invalid\n"
            f"[credential]\n\thelper = store --file {self.credentials}\n"
        )
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1"}

    def run_script(self, name, args=(), stdin="", env=None):
        return subprocess.run(
            [sys.executable, "-B", f"scripts/{name}", *args],
            cwd=self.project,
            input=stdin,
            text=True,
            capture_output=True,
            env={**self.env, **(env or {})},
            timeout=120,
        )

    def test_release_replaces_the_same_version_and_attaches_the_plugin_and_the_manual(self):
        subprocess.run([sys.executable, "-B", "scripts/build.py"], cwd=self.project, check=True, capture_output=True)
        manual = self.project / "dist" / f"UNO-Overlays-{VERSION}-Manual.pdf"
        manual.write_bytes(b"%PDF-1.7 test")  # scripts/build_manual.py has its own test (test_manual)
        self.forgejo.tags[f"v{VERSION}"] = "c0ffee"
        env = {
            "GITHUB_SERVER_URL": self.forgejo.url,
            "GITHUB_REPOSITORY": "owner/name",
            "GITHUB_REF_NAME": f"v{VERSION}",
            "FORGEJO_TOKEN": TOKEN,
            "BUILD_COMMIT": "c0ffee",
        }
        for _ in range(2):
            result = self.run_script("forgejo_release.py", env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
        releases = self.forgejo.repos["owner/name"]["releases"]
        mine = [r for r in releases.values() if r["tag"] == f"v{VERSION}"]
        self.assertEqual(len(mine), 1, "only the newest build of a version remains")
        (release,) = mine
        zip_file = self.project / "dist" / f"opendeck-uno-overlays-{VERSION}-linux.plugin.zip"
        self.assertEqual(release["data"]["name"], f"UNO Overlays {VERSION}")
        self.assertIn("Gatilhos", release["data"]["body"], "notes come from the CHANGELOG")
        self.assertIn(manual.name, release["data"]["body"], "the SHA-256 of both files is in the notes")
        self.assertEqual(
            release["assets"],
            [
                {"field": "attachment", "name": zip_file.name, "data": zip_file.read_bytes()},
                {"field": "attachment", "name": manual.name, "data": manual.read_bytes()},
            ],
        )
        self.assertTrue(all(auth == f"token {TOKEN}" for _, _, auth in self.forgejo.calls))

        self.forgejo.tags[f"v{VERSION}"] = "newer"  # the tag moved: a newer run builds it
        result = self.run_script("forgejo_release.py", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Nothing published", result.stdout)
        self.assertEqual(release, next(r for r in releases.values() if r["tag"] == f"v{VERSION}"), "untouched")

        result = self.run_script("forgejo_release.py", env={**env, "GITHUB_REF_NAME": "v9.9.9"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match the plugin version", result.stderr)

    def remote_git(self, *args):
        remote = self.forgejo.git_root / "owner" / "name.git"
        return subprocess.run(
            ["git", "--git-dir", str(remote), *args], capture_output=True, text=True, check=True, env=self.env
        ).stdout

    def test_publish_adds_a_commit_on_top_of_the_history_and_never_deletes(self):
        old = self.work / "old"
        url = self.forgejo.git_root / "owner" / "name.git"
        subprocess.run(["git", "clone", "--quiet", str(url), str(old)], check=True, env=self.env, capture_output=True)
        (old / "old.txt").write_text("old history")
        for step in (["add", "old.txt"], ["commit", "--quiet", "-m", "old"], ["push", "--quiet", "origin", "main"]):
            subprocess.run(["git", *step], cwd=old, check=True, env=self.env)
        host = self.forgejo.url.removeprefix("http://")
        self.credentials.write_text(f"http://owner:{TOKEN}@{host}\n")
        args = ["--server", self.forgejo.url, "--repo", "owner/name"]

        result = self.run_script("forgejo_publish.py", args)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        log = self.remote_git("log", "--format=%s", "main").split()
        self.assertEqual(log[:4], ["UNO", "Overlays", VERSION, "old"], "the new commit sits on the old history")
        self.assertEqual(self.remote_git("tag").split(), [f"v{VERSION}"])
        files = self.remote_git("ls-tree", "-r", "--name-only", "main").split()
        self.assertNotIn("old.txt", files, "the commit has exactly this project")
        self.assertIn("CHANGELOG.md", files)
        self.assertIn("v1.0.0", str(self.forgejo.repos["owner/name"]["releases"]), "earlier releases stay")
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

        (self.project / "NOTE.md").write_text("fix of a failed build")
        result = self.run_script("forgejo_publish.py", args)  # the tag exists without a release: it moves
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        tagged = self.remote_git("rev-list", "-n", "1", f"v{VERSION}").strip()
        self.assertEqual(tagged, self.remote_git("rev-parse", "main").strip(), "the tag moved to the new commit")
        self.assertEqual(len(self.remote_git("log", "--format=%H", "main").split()), 3, "nothing was rewritten")

        releases = self.forgejo.repos["owner/name"]["releases"]
        releases[999] = {"tag": f"v{VERSION}"}
        result = self.run_script("forgejo_publish.py", args)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already published", result.stderr)

    def test_reset_backs_up_deletes_recreates_and_pushes_one_commit_with_the_tag(self):
        old_commit = self.work / "old"
        subprocess.run(
            ["git", "clone", "--quiet", str(self.forgejo.git_root / "owner" / "name.git"), str(old_commit)],
            check=True,
            env=self.env,
            capture_output=True,
        )
        (old_commit / "old.txt").write_text("old history")
        for step in (["add", "old.txt"], ["commit", "--quiet", "-m", "old"], ["push", "--quiet", "origin", "main"]):
            subprocess.run(["git", *step], cwd=old_commit, check=True, env=self.env)
        args = ["--server", self.forgejo.url, "--repo", "owner/name"]
        remote = self.forgejo.git_root / "owner" / "name.git"
        host = self.forgejo.url.removeprefix("http://")
        self.credentials.write_text(f"http://owner:old-password@{host}\n")

        result = self.run_script("forgejo_reset.py", args, stdin=f"{TOKEN}\nwrong\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("saved credential was refused", result.stdout, "an old password is not a token")
        self.assertIn("cancelled", result.stderr)
        self.assertIn("owner/name", self.forgejo.repos, "nothing is deleted without the typed confirmation")
        saved = self.credentials.read_text()
        self.assertEqual((saved.count(TOKEN), "old-password" in saved), (1, False), "the token replaces the password")

        result = self.run_script("forgejo_reset.py", args, stdin="name\n")  # no token typed this time
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        repo = self.forgejo.repos["owner/name"]
        self.assertEqual(repo["releases"], {}, "the old releases went with the old repository")
        self.assertEqual((repo["private"], repo["description"]), (True, "old"), "same visibility and description")
        self.assertIs(repo.get("has_actions"), True)
        (backup,) = self.work.glob("name-backup-*.git")
        backed_up = subprocess.run(
            ["git", "--git-dir", str(backup), "log", "--format=%s", "main"], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(backed_up, "old\n", "the old history is mirrored locally before the delete")
        log = subprocess.run(
            ["git", "--git-dir", str(remote), "log", "--format=%s", "main"],
            capture_output=True,
            text=True,
            check=True,
            env=self.env,
        ).stdout.split("\n")
        tags = subprocess.run(
            ["git", "--git-dir", str(remote), "tag"], capture_output=True, text=True, check=True
        ).stdout
        self.assertEqual(log[:2], [f"UNO Overlays {VERSION}", ""], "a single commit")
        self.assertEqual(tags.split(), [f"v{VERSION}"])
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

        result = self.run_script("forgejo_reset.py", args, stdin=f"{TOKEN}\nname\n")
        self.assertIn("already has a .git folder", result.stderr, "never reuses an existing local history")


if __name__ == "__main__":
    unittest.main()
