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


VERSION = 1
ITERATIONS = 600_000
HEADER = b"lecture-slides-to-obsidian:mineru-token:v1\0"
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "state" / "mineru-api-token.enc.json"
OPENSSL_ENV_NAME = "LECTURE_SKILL_TOKEN_PASSPHRASE"


class TokenStoreError(RuntimeError):
    pass


def _openssl(data: bytes, passphrase: str, decrypt: bool = False) -> bytes:
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
    environment[OPENSSL_ENV_NAME] = passphrase
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


def _mac_key(passphrase: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, iterations, dklen=32
    )


def store_token(token: str, passphrase: str, path: Path = DEFAULT_PATH) -> Path:
    token = token.strip()
    if not token:
        raise TokenStoreError("MinerU API token cannot be empty")
    if len(passphrase) < 12:
        raise TokenStoreError("Encryption passphrase must contain at least 12 characters")

    ciphertext = _openssl(token.encode("utf-8"), passphrase)
    mac_salt = secrets.token_bytes(16)
    mac_key = _mac_key(passphrase, mac_salt, ITERATIONS)
    digest = hmac.new(mac_key, HEADER + ciphertext, hashlib.sha256).digest()
    payload = {
        "version": VERSION,
        "cipher": "aes-256-cbc",
        "cipher_kdf": "openssl-pbkdf2-hmac-sha256",
        "cipher_iterations": ITERATIONS,
        "integrity": "hmac-sha256",
        "mac_kdf": "pbkdf2-hmac-sha256",
        "mac_iterations": ITERATIONS,
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


def load_token(passphrase: str, path: Path = DEFAULT_PATH) -> str:
    path = Path(path)
    if not path.is_file():
        raise TokenStoreError(f"Encrypted token file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != VERSION:
            raise TokenStoreError("Unsupported encrypted token version")
        if payload.get("cipher_iterations") != ITERATIONS or payload.get("mac_iterations") != ITERATIONS:
            raise TokenStoreError("Unexpected token-store KDF settings")
        ciphertext = base64.b64decode(payload["ciphertext"], validate=True)
        mac_salt = base64.b64decode(payload["mac_salt"], validate=True)
        supplied_mac = base64.b64decode(payload["mac"], validate=True)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise TokenStoreError(f"Malformed encrypted token file: {exc}") from exc

    mac_key = _mac_key(passphrase, mac_salt, ITERATIONS)
    expected_mac = hmac.new(mac_key, HEADER + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise TokenStoreError("Wrong passphrase or encrypted token file was modified")

    plaintext = _openssl(ciphertext, passphrase, decrypt=True)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    set_parser = subparsers.add_parser("set", help="Store or replace the encrypted token")
    set_parser.add_argument(
        "--token-stdin",
        action="store_true",
        help="Read one token line from stdin; never pass the token as an argument",
    )
    subparsers.add_parser("verify", help="Verify passphrase and encrypted file without printing token")
    subparsers.add_parser("status", help="Show whether encrypted token storage is configured")
    delete_parser = subparsers.add_parser("delete", help="Delete the encrypted token file")
    delete_parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()

    try:
        if args.command == "set":
            token = sys.stdin.readline().rstrip("\r\n") if args.token_stdin else getpass.getpass("MinerU API token (hidden): ")
            passphrase = getpass.getpass("Encryption passphrase (hidden): ")
            confirmation = getpass.getpass("Confirm passphrase: ")
            if passphrase != confirmation:
                raise TokenStoreError("Passphrases do not match")
            path = store_token(token, passphrase)
            print(f"Encrypted MinerU token stored at {path}")
            return 0
        if args.command == "verify":
            passphrase = getpass.getpass("Encryption passphrase (hidden): ")
            load_token(passphrase)
            print("Encrypted MinerU token verified")
            return 0
        if args.command == "status":
            if DEFAULT_PATH.is_file():
                mode = DEFAULT_PATH.stat().st_mode & 0o777
                print(f"configured: {DEFAULT_PATH} mode={mode:04o}")
                return 0
            print(f"not configured: {DEFAULT_PATH}")
            return 1
        if args.command == "delete":
            if not args.confirm:
                raise TokenStoreError("delete requires --confirm")
            removed = delete_token()
            print("Encrypted MinerU token removed" if removed else "Encrypted MinerU token was not configured")
            return 0
    except TokenStoreError as exc:
        print(f"token-store error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
