#!/usr/bin/env python3
"""Encrypt and manage the MinerU API token inside the installed skill directory."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


VERSION = 2
ITERATIONS = 600_000
HEADER = b"lecture-slides-to-obsidian:mineru-token:v2\0"
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "state" / "mineru-api-token.enc.json"
OPENSSL_ENV_NAME = "LECTURE_SKILL_TOKEN_WRAPPING_SECRET"
KEYCHAIN_SERVICE = "lecture-slides-to-obsidian.mineru-token-key"


class TokenStoreError(RuntimeError):
    pass


def keychain_account(path: Path = DEFAULT_PATH) -> str:
    skill_root = Path(path).resolve().parent.parent
    digest = hashlib.sha256(str(skill_root).encode("utf-8")).hexdigest()[:24]
    return f"install-{digest}"


def _security(arguments: list[str]) -> subprocess.CompletedProcess:
    executable = shutil.which("security")
    if sys.platform != "darwin" or executable is None:
        raise TokenStoreError("automatic token unlock currently requires macOS Keychain")
    return subprocess.run(
        [executable, *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def get_wrapping_secret(path: Path = DEFAULT_PATH) -> str:
    result = _security([
        "find-generic-password", "-s", KEYCHAIN_SERVICE,
        "-a", keychain_account(path), "-w",
    ])
    if result.returncode != 0 or not result.stdout.strip():
        raise TokenStoreError("Keychain wrapping key is missing; configure the token again")
    return result.stdout.strip()


def get_or_create_wrapping_secret(path: Path = DEFAULT_PATH) -> str:
    try:
        return get_wrapping_secret(path)
    except TokenStoreError as exc:
        if "wrapping key is missing" not in str(exc):
            raise
    secret = secrets.token_urlsafe(32)
    result = _security([
        "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE,
        "-a", keychain_account(path), "-w", secret,
        "-T", "/usr/bin/security",
    ])
    if result.returncode != 0:
        raise TokenStoreError(
            "failed to create Keychain wrapping key: "
            + result.stderr.strip()
        )
    return secret


def delete_wrapping_secret(path: Path = DEFAULT_PATH) -> bool:
    result = _security([
        "delete-generic-password", "-s", KEYCHAIN_SERVICE,
        "-a", keychain_account(path),
    ])
    return result.returncode == 0


def _openssl(data: bytes, wrapping_secret: str, decrypt: bool = False) -> bytes:
    executable = shutil.which("openssl")
    if executable is None:
        raise TokenStoreError("OpenSSL is required but was not found")
    command = [
        executable,
        "enc",
        "-aes-256-cbc",
        "-pbkdf2",
        "-iter",
        str(ITERATIONS),
        "-md",
        "sha256",
        "-pass",
        f"env:{OPENSSL_ENV_NAME}",
    ]
    command.append("-d" if decrypt else "-salt")
    environment = os.environ.copy()
    environment[OPENSSL_ENV_NAME] = wrapping_secret
    try:
        result = subprocess.run(
            command,
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=environment,
        )
    finally:
        environment.pop(OPENSSL_ENV_NAME, None)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise TokenStoreError(f"OpenSSL operation failed: {message}")
    return result.stdout


def _mac_key(wrapping_secret: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", wrapping_secret.encode("utf-8"), salt, iterations, dklen=32
    )


def store_token(token: str, wrapping_secret: str, path: Path = DEFAULT_PATH) -> Path:
    token = token.strip()
    if not token:
        raise TokenStoreError("MinerU API token cannot be empty")
    if len(wrapping_secret) < 32:
        raise TokenStoreError("Keychain wrapping secret is unexpectedly short")

    ciphertext = _openssl(token.encode("utf-8"), wrapping_secret)
    mac_salt = secrets.token_bytes(16)
    mac_key = _mac_key(wrapping_secret, mac_salt, ITERATIONS)
    digest = hmac.new(mac_key, HEADER + ciphertext, hashlib.sha256).digest()
    payload = {
        "version": VERSION,
        "cipher": "aes-256-cbc",
        "cipher_kdf": "openssl-pbkdf2-hmac-sha256",
        "cipher_iterations": ITERATIONS,
        "integrity": "hmac-sha256",
        "mac_kdf": "pbkdf2-hmac-sha256",
        "mac_iterations": ITERATIONS,
        "wrapping_key_backend": "macos-keychain",
        "keychain_service": KEYCHAIN_SERVICE,
        "keychain_account": keychain_account(path),
        "mac_salt": base64.b64encode(mac_salt).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        "mac": base64.b64encode(digest).decode("ascii"),
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, prefix=".mineru-token-", delete=False
        ) as handle:
            temp_name = Path(handle.name)
            os.chmod(handle.name, 0o600)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        os.chmod(path, 0o600)
    finally:
        if temp_name is not None and temp_name.exists():
            temp_name.unlink()
    return path


def load_token(wrapping_secret: str, path: Path = DEFAULT_PATH) -> str:
    path = Path(path)
    if not path.is_file():
        raise TokenStoreError(f"Encrypted token file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != VERSION:
            raise TokenStoreError("Unsupported encrypted token version")
        if payload.get("cipher_iterations") != ITERATIONS or payload.get("mac_iterations") != ITERATIONS:
            raise TokenStoreError("Unexpected token-store KDF settings")
        if payload.get("wrapping_key_backend") != "macos-keychain":
            raise TokenStoreError("Unsupported wrapping-key backend")
        if payload.get("keychain_service") != KEYCHAIN_SERVICE:
            raise TokenStoreError("Unexpected Keychain service identifier")
        if payload.get("keychain_account") != keychain_account(path):
            raise TokenStoreError("Encrypted token belongs to a different skill installation path")
        ciphertext = base64.b64decode(payload["ciphertext"], validate=True)
        mac_salt = base64.b64decode(payload["mac_salt"], validate=True)
        supplied_mac = base64.b64decode(payload["mac"], validate=True)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise TokenStoreError(f"Malformed encrypted token file: {exc}") from exc

    mac_key = _mac_key(wrapping_secret, mac_salt, ITERATIONS)
    expected_mac = hmac.new(mac_key, HEADER + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise TokenStoreError("Keychain key mismatch or encrypted token file was modified")

    plaintext = _openssl(ciphertext, wrapping_secret, decrypt=True)
    try:
        token = plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TokenStoreError("Decrypted token is not valid UTF-8") from exc
    if not token:
        raise TokenStoreError("Decrypted token is empty")
    return token


def delete_token(path: Path = DEFAULT_PATH) -> bool:
    path = Path(path)
    if path.exists():
        path.unlink()
        return True
    return False


def store_token_auto(token: str, path: Path = DEFAULT_PATH) -> Path:
    return store_token(token, get_or_create_wrapping_secret(path), path)


def load_token_auto(path: Path = DEFAULT_PATH) -> str:
    return load_token(get_wrapping_secret(path), path)


def delete_token_auto(path: Path = DEFAULT_PATH) -> tuple[bool, bool]:
    file_removed = delete_token(path)
    key_removed = delete_wrapping_secret(path)
    return file_removed, key_removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set", help="Store or replace the encrypted token")
    set_parser.add_argument(
        "--token-stdin",
        action="store_true",
        help="Read one token line from stdin; never pass the token as an argument",
    )
    subparsers.add_parser("verify", help="Verify Keychain key and encrypted file without printing token")
    subparsers.add_parser("status", help="Show whether encrypted token storage is configured")
    delete_parser = subparsers.add_parser("delete", help="Delete the encrypted token file")
    delete_parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    try:
        if args.command == "set":
            token = sys.stdin.readline().rstrip("\r\n") if args.token_stdin else getpass.getpass("MinerU API token (hidden): ")
            path = store_token_auto(token)
            print(f"Encrypted MinerU token stored at {path}; wrapping key stored in macOS Keychain")
            return 0
        if args.command == "verify":
            load_token_auto()
            print("Encrypted MinerU token and Keychain wrapping key verified")
            return 0
        if args.command == "status":
            if DEFAULT_PATH.is_file():
                get_wrapping_secret()
                mode = DEFAULT_PATH.stat().st_mode & 0o777
                print(f"configured: {DEFAULT_PATH} mode={mode:04o} keychain=available")
                return 0
            print(f"not configured: {DEFAULT_PATH}")
            return 1
        if args.command == "delete":
            if not args.confirm:
                raise TokenStoreError("delete requires --confirm")
            file_removed, key_removed = delete_token_auto()
            print(
                "MinerU credential state removed"
                if file_removed or key_removed
                else "MinerU credential state was not configured"
            )
            return 0
    except TokenStoreError as exc:
        print(f"token-store error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
