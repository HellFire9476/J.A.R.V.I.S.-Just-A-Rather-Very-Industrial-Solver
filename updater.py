import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass


_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_SHA256_PATTERN = re.compile(r"^sha256:([a-fA-F0-9]{64})$")
_MAX_RELEASE_SIZE = 200 * 1024 * 1024


@dataclass(frozen=True)
class ReleaseInfo:
    version: tuple[int, int, int]
    tag: str
    download_url: str
    sha256: str
    size: int
    release_url: str


def parse_version(value):
    match = _VERSION_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Version GitHub invalide : {value!r}")
    return tuple(int(part) for part in match.groups())


def parse_release(repository, payload):
    if payload.get("draft") or payload.get("prerelease"):
        raise ValueError("La dernière version publiée est un brouillon ou une préversion.")

    tag = payload.get("tag_name")
    version = parse_version(tag) if isinstance(tag, str) else None
    expected_prefix = f"https://github.com/{repository}/releases/download/"
    release_url = payload.get("html_url")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise ValueError("La publication GitHub ne contient pas de liste de fichiers.")

    asset = next(
        (item for item in assets if isinstance(item, dict) and item.get("name") == "JARVIS.exe"),
        None,
    )
    if asset is None:
        raise ValueError("La publication ne contient pas JARVIS.exe.")

    download_url = asset.get("browser_download_url")
    if not isinstance(download_url, str) or not download_url.startswith(expected_prefix):
        raise ValueError("L'adresse de téléchargement ne correspond pas au dépôt attendu.")

    digest = asset.get("digest")
    if not isinstance(digest, str):
        raise ValueError("GitHub ne fournit pas d'empreinte SHA-256 pour cet exécutable.")
    digest_match = _SHA256_PATTERN.fullmatch(digest)
    if digest_match is None:
        raise ValueError("GitHub ne fournit pas d'empreinte SHA-256 pour cet exécutable.")

    size = asset.get("size")
    if not isinstance(size, int) or not 0 < size <= _MAX_RELEASE_SIZE:
        raise ValueError("La taille de l'exécutable publiée est invalide.")
    if not isinstance(release_url, str) or not release_url.startswith(
        f"https://github.com/{repository}/releases/tag/"
    ):
        raise ValueError("L'adresse de la publication GitHub est invalide.")

    return ReleaseInfo(
        version=version,
        tag=tag,
        download_url=download_url,
        sha256=digest_match.group(1).lower(),
        size=size,
        release_url=release_url,
    )


def fetch_latest_release(repository, timeout=10):
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "JARVIS-Satisfactory-Updater",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub a répondu avec le code HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise RuntimeError("Impossible de joindre GitHub. Vérifie ta connexion Internet.") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("GitHub a renvoyé une réponse de version invalide.") from error
    return parse_release(repository, payload)


def download_release_asset(release, timeout=60):
    request = urllib.request.Request(
        release.download_url,
        headers={"User-Agent": "JARVIS-Satisfactory-Updater"},
    )
    file_descriptor, path = tempfile.mkstemp(prefix="JARVIS-update-", suffix=".exe")
    digest = hashlib.sha256()
    received = 0
    try:
        with os.fdopen(file_descriptor, "wb") as target:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if received > release.size or received > _MAX_RELEASE_SIZE:
                        raise RuntimeError("L'exécutable téléchargé dépasse la taille annoncée.")
                    digest.update(chunk)
                    target.write(chunk)
        if received != release.size:
            raise RuntimeError("Le téléchargement est incomplet.")
        if digest.hexdigest() != release.sha256:
            raise RuntimeError("L'empreinte SHA-256 téléchargée ne correspond pas à GitHub.")
        return path
    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        try:
            os.remove(path)
        except OSError:
            pass
        raise


def _powershell_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def launch_windows_updater(downloaded_exe, target_exe, process_id):
    if os.name != "nt":
        raise OSError("La mise à jour automatique est disponible uniquement sous Windows.")

    backup_exe = os.path.join(
        tempfile.gettempdir(), f"JARVIS-{process_id}-previous.exe"
    )
    script_path = os.path.join(
        tempfile.gettempdir(), f"JARVIS-update-{process_id}.ps1"
    )
    script = f"""$ErrorActionPreference = 'Stop'
$source = {_powershell_literal(downloaded_exe)}
$target = {_powershell_literal(target_exe)}
$backup = {_powershell_literal(backup_exe)}
$processId = {int(process_id)}
try {{
    try {{
        Wait-Process -Id $processId -Timeout 120 -ErrorAction Stop
    }} catch {{
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {{
            throw 'J.A.R.V.I.S. ne s''est pas fermé ; la mise à jour est annulée.'
        }}
    }}
    if (Test-Path -LiteralPath $backup) {{ Remove-Item -LiteralPath $backup -Force }}
    if (Test-Path -LiteralPath $target) {{ Move-Item -LiteralPath $target -Destination $backup -Force }}
    try {{
        Move-Item -LiteralPath $source -Destination $target -Force
        Start-Process -FilePath $target
    }} catch {{
        if (Test-Path -LiteralPath $target) {{ Remove-Item -LiteralPath $target -Force }}
        if (Test-Path -LiteralPath $backup) {{ Move-Item -LiteralPath $backup -Destination $target -Force }}
        throw
    }}
}} catch {{
    $message = "La mise à jour n'a pas pu être installée : $($_.Exception.Message)"
    try {{
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show($message, 'Mise à jour J.A.R.V.I.S.', 'OK', 'Error') | Out-Null
    }} catch {{}}
}} finally {{
    if (Test-Path -LiteralPath $source) {{ Remove-Item -LiteralPath $source -Force }}
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
}}
"""
    try:
        with open(script_path, "w", encoding="utf-8") as script_file:
            script_file.write(script)
        powershell = os.path.join(
            os.environ.get("SystemRoot", r"C:\Windows"),
            "System32",
            "WindowsPowerShell",
            "v1.0",
            "powershell.exe",
        )
        subprocess.Popen(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-File",
                script_path,
            ],
            close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    except Exception:
        try:
            os.remove(script_path)
        except OSError:
            pass
        raise
