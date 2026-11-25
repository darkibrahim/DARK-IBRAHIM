# ----------------------------------------------------------------------
# DARK-IBRAHIM - Local AI Software & APK Builder
# Developer : DARK IBRAHIM
# Title     : Bug Bounty Hunter & Cyber Security Expert
# Facebook  : https://www.facebook.com/profile.php?id=61580661413217
# GitHub    : https://github.com/darkibrahim
# Telegram  : @Hunter_1B4H14
# ----------------------------------------------------------------------
"""Tests: manifest, Android project generation, permission policy, APK validation."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from apk_generator import apk_validator
from apk_generator.android_builder import (
    _android_string, build_project_files, default_package, web_root, write_project,
)
from apk_generator.manifest_generator import generate_manifest
from security.permissions import filter_permissions
from security.validator import ValidationError, validate_app_name, validate_package_name

WEB = {"index.html": "<!DOCTYPE html><html><body>hi</body></html>", "style.css": "body{}", "app.js": "1;"}


class PermissionTests(unittest.TestCase):
    def test_blocked_and_unknown_permissions_are_rejected(self):
        allowed, rejected = filter_permissions(["INTERNET", "READ_SMS", "android.permission.CAMERA", "FOO"])
        self.assertEqual(allowed, ["android.permission.INTERNET"])
        self.assertEqual(len(rejected), 3)

    def test_defaults(self):
        allowed, _ = filter_permissions(None)
        self.assertIn("android.permission.INTERNET", allowed)


class ManifestTests(unittest.TestCase):
    def test_manifest_is_valid_xml(self):
        root = ET.fromstring(generate_manifest("com.example.demo", ["INTERNET", "READ_SMS"]))
        names = [p.attrib["{http://schemas.android.com/apk/res/android}name"] for p in root.findall("uses-permission")]
        self.assertEqual(names, ["android.permission.INTERNET"])

    def test_invalid_package_rejected(self):
        for bad in ("Com.Example", "single", "com.class.app", "com.example.", "1com.app"):
            with self.subTest(package=bad), self.assertRaises(ValidationError):
                validate_package_name(bad)

    def test_app_name_rules(self):
        self.assertEqual(validate_app_name("My App"), "My App")
        with self.assertRaises(ValidationError):
            validate_app_name("<script>")


class BuilderTests(unittest.TestCase):
    def test_default_package_is_valid(self):
        for name in ("notes-app", "123", "দিগন্ত", "x"):
            self.assertTrue(validate_package_name(default_package(name)))

    def test_escape(self):
        self.assertEqual(_android_string("Tom's & Jerry"), "Tom\\'s &amp; Jerry")
        self.assertTrue(_android_string("@home").startswith("\\@"))

    def test_project_generation_and_validation(self):
        files = build_project_files("Demo App", "com.example.demo", WEB)
        with tempfile.TemporaryDirectory() as tmp:
            android = write_project(Path(tmp), files)
            result = apk_validator.validate_project(android)
            self.assertTrue(result["valid"], result["problems"])
            self.assertEqual(result["package"], "com.example.demo")
            self.assertTrue((android / "app/src/main/assets/www/app.js").is_file())

    def test_template_pages_are_rejected(self):
        self.assertIsNone(web_root({"index.html": "{{ title }}"}))
        with self.assertRaises(ValueError):
            build_project_files("Demo", "com.example.demo", {"index.html": "{% block %}"})

    def test_www_prefix(self):
        files = build_project_files("Demo", "com.example.demo", {"www/index.html": "<html></html>", "other.js": "x"})
        self.assertIn("android/app/src/main/assets/www/index.html", files)
        self.assertNotIn("android/app/src/main/assets/www/other.js", files)


class ApkValidatorTests(unittest.TestCase):
    def test_fake_apk_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.apk"
            with zipfile.ZipFile(good, "w") as zf:
                zf.writestr("AndroidManifest.xml", "x")
                zf.writestr("classes.dex", "x")
                zf.writestr("assets/www/index.html", "x")
            self.assertTrue(apk_validator.validate_apk(good)["valid"])
            incomplete = Path(tmp) / "inc.apk"
            with zipfile.ZipFile(incomplete, "w") as zf:
                zf.writestr("AndroidManifest.xml", "x")
            self.assertFalse(apk_validator.validate_apk(incomplete)["valid"])
            broken = Path(tmp) / "broken.apk"
            broken.write_bytes(b"junk")
            self.assertFalse(apk_validator.validate_apk(broken)["valid"])
            self.assertFalse(apk_validator.validate_apk(Path(tmp) / "missing.apk")["valid"])


if __name__ == "__main__":
    unittest.main()
