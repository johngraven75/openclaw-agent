import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import app as openclaw


class BrowserBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tmp.name) / "openclaw_config.json"
        self.config_patcher = mock.patch.object(openclaw, "CONFIG_PATH", self.config_path)
        self.config_patcher.start()
        self.client = openclaw.app.test_client()

    def tearDown(self):
        self.config_patcher.stop()
        self.tmp.cleanup()

    def test_rejects_cross_origin_mutation(self):
        response = self.client.post(
            "/api/settings",
            json={"provider": "local"},
            headers={"Origin": "https://attacker.example"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.get_json()["ok"])
        self.assertFalse(self.config_path.exists())

    def test_accepts_same_origin_mutation_and_local_non_browser_clients(self):
        same_origin = self.client.post(
            "/api/settings",
            json={"provider": "local"},
            headers={"Origin": "http://localhost"},
        )
        local_client = self.client.post("/api/settings", json={"reasoning_style": "plan-act-check"})

        self.assertEqual(same_origin.status_code, 200)
        self.assertEqual(local_client.status_code, 200)

    def test_rejects_fetch_metadata_marked_cross_site_without_origin(self):
        response = self.client.post(
            "/api/settings",
            json={"provider": "local"},
            headers={"Sec-Fetch-Site": "cross-site"},
        )

        self.assertEqual(response.status_code, 403)

    def test_home_uses_local_executable_assets_and_security_policy(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/js/icons.js', html)
        self.assertNotIn("unpkg.com", html)
        self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])

    def test_pending_chat_status_is_not_added_to_conversation_history(self):
        script = (Path(openclaw.ASSET_ROOT) / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('const pending = renderMessage("assistant", "Thinking...")', script)
        self.assertNotIn('addMessage("assistant", "Thinking...")', script)
        self.assertIn("messages: history", script)

    def test_public_build_identity_is_sequential_and_consistent(self):
        self.assertEqual(openclaw.VERSION, "1.0.10")
        self.assertEqual(openclaw.BUILD_LABEL, "Build 1.0.10")


class OpenVsxBoundaryTests(unittest.TestCase):
    def test_allows_only_openvsx_https_downloads(self):
        allowed = "https://open-vsx.org/api/example/tool/1.2.3/file/example.tool.vsix"
        self.assertEqual(openclaw.validated_openvsx_download_url(allowed), allowed)

        rejected = [
            "http://open-vsx.org/api/example.vsix",
            "https://open-vsx.org.attacker.example/example.vsix",
            "https://attacker.example/example.vsix",
            "https://user@open-vsx.org/example.vsix",
            "https://open-vsx.org:444/example.vsix",
            "file:///tmp/example.vsix",
        ]
        for url in rejected:
            with self.subTest(url=url), self.assertRaises(ValueError):
                openclaw.validated_openvsx_download_url(url)

    def test_rejects_plugin_identifiers_that_can_escape_the_store(self):
        for value in ["", ".", "..", "../escape", "name/child", "name\\child", "name:drive"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                openclaw.validated_plugin_component(value, "Extension name")
        self.assertEqual(openclaw.validated_plugin_component("publisher.tool-1", "Extension name"), "publisher.tool-1")

    def test_extracts_valid_vsix_and_reads_package_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "valid.vsix"
            destination = Path(tmp) / "extracted"
            package = {"name": "safe-extension", "publisher": "example", "version": "1.0.0"}
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("extension/package.json", json.dumps(package))
                archive.writestr("extension/index.js", "module.exports = {};\n")

            metadata = openclaw.extract_package_json(archive_path, destination)

            self.assertEqual(metadata, package)
            self.assertEqual((destination / "extension" / "index.js").read_text(), "module.exports = {};\n")

    def test_rejects_traversal_absolute_and_symlink_members_before_writing(self):
        unsafe_members = ["../escape.txt", "..\\escape.txt", "/absolute.txt", "C:/drive.txt"]
        for member_name in unsafe_members:
            with self.subTest(member_name=member_name), tempfile.TemporaryDirectory() as tmp:
                archive_path = Path(tmp) / "unsafe.vsix"
                destination = Path(tmp) / "extracted"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("extension/package.json", "{}")
                    archive.writestr(member_name, "escape")

                with self.assertRaises(ValueError):
                    openclaw.extract_package_json(archive_path, destination)
                self.assertFalse((Path(tmp) / "escape.txt").exists())
                self.assertFalse(destination.exists())

        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "symlink.vsix"
            destination = Path(tmp) / "extracted"
            symlink = zipfile.ZipInfo("extension/link")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("extension/package.json", "{}")
                archive.writestr(symlink, "../../outside")

            with self.assertRaises(ValueError):
                openclaw.extract_package_json(archive_path, destination)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
