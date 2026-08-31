# Skill-owned runtime state

The installed skill creates two ignored runtime files here:

- `course-registry.yaml` contains semester/course routing.
- `mineru-api-token.enc.json` contains the MinerU token encrypted at rest.

The encrypted token uses OpenSSL AES-256-CBC with PBKDF2-HMAC-SHA256 and an independent HMAC-SHA256 integrity key. A random wrapping key is stored in macOS Keychain, not beside the ciphertext. The file is mode `0600`; this directory is set to `0700` when written.

Keep all runtime backups here so deleting the skill removes its state. Do not store plaintext credentials, Canvas sessions, or course content here.

An updater that replaces the whole skill directory must preserve this directory and restore it in place. Package updates must never replace a real registry with the example file.

Use `course-registry.example.yaml` as the routing schema example. Configure and verify the encrypted token without a human passphrase:

```bash
../scripts/token-store.py set
../scripts/token-store.py verify
../scripts/token-store.py status
```

To remove all local routing and token state before uninstall or before a manager creates a backup, run:

```bash
../scripts/purge-state.sh --confirm
```
