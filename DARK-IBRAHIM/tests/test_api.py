# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Tests: REST API through Flask's test client (offline, template mode)."""
import time
import unittest

from backend.api import create_app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = create_app().test_client()

    def wait(self, job_id, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            job = self.client.get(f"/api/jobs/{job_id}").json
            if job["status"] in ("done", "error"):
                return job
            time.sleep(0.1)
        self.fail("job timed out")

    def build_project(self, prompt="A static website for my portfolio"):
        resp = self.client.post("/api/projects/build", json={"prompt": prompt, "mode": "template"})
        self.assertEqual(resp.status_code, 202)
        job = self.wait(resp.json["job_id"])
        self.assertEqual(job["status"], "done", job.get("error"))
        return job["result"]

    def test_health_and_headers(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["brand"]["developer"], "DARK IBRAHIM")
        self.assertFalse(resp.json["ollama"]["ollama_available"])
        self.assertEqual(resp.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", resp.headers["Content-Security-Policy"])

    def test_frontend_is_served(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"DARK-IBRAHIM", resp.data)
        self.assertEqual(self.client.get("/app.js").status_code, 200)

    def test_validation_errors(self):
        self.assertEqual(self.client.post("/api/projects/build", json={"prompt": "x"}).status_code, 400)
        self.assertEqual(self.client.post("/api/projects/build", json={"prompt": "valid prompt", "mode": "bad"}).status_code, 400)
        self.assertEqual(self.client.post("/api/projects/build", json={"prompt": "valid prompt", "project_type": "x"}).status_code, 400)
        self.assertEqual(self.client.get("/api/jobs/not-an-id").status_code, 400)
        self.assertEqual(self.client.get("/api/projects/" + "0" * 32).status_code, 404)
        self.assertEqual(self.client.get("/api/nothing").status_code, 404)

    def test_build_download_preview_delete(self):
        result = self.build_project()
        pid = result["id"]
        download = self.client.get(result["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download.data.startswith(b"PK"))

        listing = self.client.get(f"/api/projects/{pid}/files").json["files"]
        self.assertIn("index.html", [f["path"] for f in listing])
        preview = self.client.get(f"/api/projects/{pid}/file?path=index.html")
        self.assertIn("DARK IBRAHIM", preview.json["content"])
        self.assertEqual(self.client.get(f"/api/projects/{pid}/file?path=../../etc/passwd").status_code, 400)
        self.assertEqual(self.client.get(f"/api/projects/{pid}/file?path=nope.html").status_code, 404)

        history = self.client.get("/api/projects").json["projects"]
        self.assertIn(pid, [p["id"] for p in history])
        self.assertEqual(self.client.delete(f"/api/projects/{pid}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{pid}").status_code, 404)

    def test_apk_flow_creates_android_project_zip(self):
        project = self.build_project("An android app with a counter")
        resp = self.client.post("/api/apk/build", json={"project_id": project["id"], "permissions": ["INTERNET", "READ_SMS"]})
        self.assertEqual(resp.status_code, 202)
        job = self.wait(resp.json["job_id"], timeout=60)
        self.assertEqual(job["status"], "done", job.get("error"))
        result = job["result"]
        self.assertIn("android.permission.INTERNET", result["permissions"])
        self.assertTrue(any("READ_SMS" in r for r in result["rejected_permissions"]))
        zipped = self.client.get(result["project_zip_url"])
        self.assertEqual(zipped.status_code, 200)
        self.assertTrue(zipped.data.startswith(b"PK"))
        self.assertEqual(self.client.get(f"/api/apk/download/{result['build_id']}/apk").status_code,
                         200 if result["apk_url"] else 404)

    def test_apk_rejects_flask_project(self):
        resp = self.client.post("/api/projects/build", json={"prompt": "A flask web dashboard", "mode": "template"})
        project = self.wait(resp.json["job_id"])["result"]
        resp = self.client.post("/api/apk/build", json={"project_id": project["id"]})
        job = self.wait(resp.json["job_id"])
        self.assertEqual(job["status"], "error")
        self.assertIn("index.html", job["error"])

    def test_apk_environment_endpoint(self):
        data = self.client.get("/api/apk/environment").json
        self.assertIn("ready", data)


if __name__ == "__main__":
    unittest.main()
