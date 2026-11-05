import os
import tempfile
import unittest
from unittest import mock

from updater import (
    ReleaseInfo,
    download_release_asset,
    launch_windows_updater,
    parse_release,
    parse_version,
)


REPOSITORY = "HellFire9476/J.A.R.V.I.S.-Just-A-Rather-Very-Industrial-Solver"
DIGEST = "a" * 64


def release_payload(**overrides):
    payload = {
        "tag_name": "v1.2.3",
        "draft": False,
        "prerelease": False,
        "html_url": f"https://github.com/{REPOSITORY}/releases/tag/v1.2.3",
        "assets": [{
            "name": "JARVIS.exe",
            "browser_download_url": f"https://github.com/{REPOSITORY}/releases/download/v1.2.3/JARVIS.exe",
            "digest": f"sha256:{DIGEST}",
            "size": 1024,
        }],
    }
    payload.update(overrides)
    return payload


class VersionParsingTests(unittest.TestCase):
    def test_parses_release_version(self):
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))

    def test_rejects_non_release_version(self):
        with self.assertRaises(ValueError):
            parse_version("latest")


class ReleaseParsingTests(unittest.TestCase):
    def test_parses_latest_executable_and_checksum(self):
        release = parse_release(REPOSITORY, release_payload())

        self.assertEqual(release.version, (1, 2, 3))
        self.assertEqual(release.sha256, DIGEST)
        self.assertEqual(release.size, 1024)

    def test_rejects_download_url_outside_configured_repository(self):
        asset = release_payload()["assets"][0]
        asset["browser_download_url"] = "https://example.com/JARVIS.exe"

        with self.assertRaises(ValueError):
            parse_release(REPOSITORY, release_payload(assets=[asset]))

    def test_rejects_missing_checksum(self):
        asset = release_payload()["assets"][0]
        asset["digest"] = None

        with self.assertRaises(ValueError):
            parse_release(REPOSITORY, release_payload(assets=[asset]))

    def test_rejects_draft_release(self):
        with self.assertRaises(ValueError):
            parse_release(REPOSITORY, release_payload(draft=True))


class DownloadVerificationTests(unittest.TestCase):
    def test_rejects_download_whose_checksum_does_not_match(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = [b"unsafe update", b""]
        release = ReleaseInfo(
            version=(1, 2, 3),
            tag="v1.2.3",
            download_url=f"https://github.com/{REPOSITORY}/releases/download/v1.2.3/JARVIS.exe",
            sha256=DIGEST,
            size=len(b"unsafe update"),
            release_url=f"https://github.com/{REPOSITORY}/releases/tag/v1.2.3",
        )
        real_mkstemp = tempfile.mkstemp
        created_files = []

        def create_temp_file(**kwargs):
            file_descriptor, path = real_mkstemp(**kwargs)
            created_files.append(path)
            return file_descriptor, path

        with mock.patch("updater.urllib.request.urlopen", return_value=response):
            with mock.patch("updater.tempfile.mkstemp", side_effect=create_temp_file):
                with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                    download_release_asset(release)

        self.assertEqual(len(created_files), 1)
        self.assertFalse(os.path.exists(created_files[0]))


@unittest.skipUnless(os.name == "nt", "Windows updater handoff test")
class WindowsUpdaterTests(unittest.TestCase):
    def test_creates_handoff_script_and_starts_it_detached(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("updater.tempfile.gettempdir", return_value=temp_dir):
                with mock.patch("updater.subprocess.Popen") as popen:
                    launch_windows_updater(r"C:\Temp\JARVIS update.exe", r"C:\Apps\JARVIS.exe", 1234)

            command = popen.call_args.args[0]
            script_path = command[-1]
            self.assertTrue(popen.call_args.kwargs["close_fds"])
            try:
                with open(script_path, encoding="utf-8") as script_file:
                    script = script_file.read()
                self.assertIn("Wait-Process", script)
                self.assertIn("MessageBox]::Show", script)
                self.assertIn("Move-Item", script)
            finally:
                os.remove(script_path)


if __name__ == "__main__":
    unittest.main()
