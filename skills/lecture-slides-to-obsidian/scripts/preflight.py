#!/usr/bin/env python3
"""Machine-readable preflight for one source document before MinerU upload."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


MAX_BYTES = 200 * 1024 * 1024
SUPPORTED = {
    ".pdf", ".png", ".jpg", ".jpeg", ".jp2", ".webp", ".gif", ".bmp",
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
}
PROFILES = {"lecture-notes", "policy-document", "paper"}
REQUIRED_SKILLS = {"obsidian-markdown", "obsidian-cli", "obsidian-canvas-designer"}
MINERU_LANGUAGES = {
    "ch", "ch_server", "en", "japan", "korean", "chinese_cht", "ta",
    "te", "ka", "el", "th", "latin", "arabic", "cyrillic",
    "east_slavic", "devanagari",
}
POLICY_HINTS = re.compile(r"(?:policy|code[-_ ]of[-_ ]conduct|regulation|handbook|guideline|rules?)", re.I)
PAPER_HINTS = re.compile(r"(?:paper|article|thesis|dissertation|journal)", re.I)


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def infer_profile(filename: str) -> str | None:
    if POLICY_HINTS.search(filename):
        return "policy-document"
    if PAPER_HINTS.search(filename):
        return "paper"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--vault-root", type=Path)
    parser.add_argument("--course")
    parser.add_argument("--profile", choices=sorted(PROFILES))
    parser.add_argument("--confirm-profile-mismatch", action="store_true")
    parser.add_argument("--language")
    parser.add_argument("--is-ocr", choices=("true", "false"))
    parser.add_argument("--loaded-skill", action="append", default=[])
    parser.add_argument("--visual-layout-refinement", action="store_true")
    parser.add_argument("--layout-model")
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument(
        "--token-file",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "state/mineru-api-token.enc.json",
    )
    args = parser.parse_args()

    errors: list[str] = []
    questions: list[dict[str, str]] = []
    checks: dict[str, object] = {}
    source = args.source.resolve()

    if not source.is_file():
        errors.append("source file does not exist")
    else:
        checks["source_size_bytes"] = source.stat().st_size
        checks["source_suffix"] = source.suffix.lower()
        if source.suffix.lower() not in SUPPORTED:
            errors.append(f"unsupported source type: {source.suffix.lower()}")
        if source.stat().st_size > MAX_BYTES:
            errors.append("source exceeds MinerU 200 MB limit")

    if args.vault_root is None:
        questions.append({"id": "vault_root", "prompt": "Obsidian vault 的目标根目录在哪儿？"})
    else:
        vault_root = args.vault_root.resolve()
        if not vault_root.is_dir():
            errors.append("vault root is not an existing directory")
        elif inside(source, vault_root):
            errors.append("source original is inside the Obsidian vault")
        checks["vault_root"] = str(vault_root)

    if not args.course:
        questions.append({"id": "course", "prompt": "这份资料属于哪门课程？"})

    suggested_profile = infer_profile(source.name)
    checks["suggested_profile"] = suggested_profile
    if args.profile is None:
        prompt = "请选择 conversion profile：lecture-notes / policy-document / paper。"
        if suggested_profile:
            prompt = f"文件名更像 {suggested_profile}；是否使用该 profile？"
        questions.append({"id": "profile", "prompt": prompt})
    elif suggested_profile and args.profile != suggested_profile and not args.confirm_profile_mismatch:
        questions.append({
            "id": "profile_mismatch",
            "prompt": f"文件名更像 {suggested_profile}，但当前选择是 {args.profile}；是否确认继续？",
        })

    if args.language is None or args.language.lower() == "auto":
        questions.append({"id": "language", "prompt": "请确认 MinerU language（例如纯英文用 en，中英混合用 ch）。"})
    elif args.language not in MINERU_LANGUAGES:
        errors.append(f"unsupported MinerU language enum: {args.language}")
    if args.is_ocr is None:
        questions.append({"id": "is_ocr", "prompt": "是否启用 OCR？请明确回答 true 或 false。"})

    loaded = set(args.loaded_skill)
    missing_skills = sorted(REQUIRED_SKILLS - loaded)
    if missing_skills:
        errors.append("helper skills not loaded through the Skill tool: " + ", ".join(missing_skills))
    checks["loaded_helper_skills"] = sorted(loaded & REQUIRED_SKILLS)
    checks["loaded_optional_skills"] = sorted(loaded & {"slide-layout-refiner"})
    checks["visual_layout_refinement"] = args.visual_layout_refinement
    if args.visual_layout_refinement:
        if "slide-layout-refiner" not in loaded:
            errors.append("optional slide-layout-refiner skill was enabled but not loaded")
        if not args.layout_model:
            questions.append({
                "id": "layout_model",
                "prompt": "请选择支持直接读取原PDF的多模态模型；推荐 MiniMax-M3。",
            })
        else:
            checks["layout_model"] = args.layout_model

    obsidian_cli = shutil.which("obsidian")
    if not args.fixture_mode and obsidian_cli is None:
        errors.append("Obsidian CLI is unavailable for renderer QA")
    elif obsidian_cli:
        checks["obsidian_cli"] = obsidian_cli
        if not args.fixture_mode:
            version = subprocess.run(
                [obsidian_cli, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if version.returncode != 0:
                errors.append("Obsidian CLI version check failed")
            else:
                checks["obsidian_cli_version"] = version.stdout.splitlines()[0].strip()

    openssl = shutil.which("openssl")
    if openssl is None:
        errors.append("OpenSSL is unavailable")
    else:
        checks["openssl"] = openssl
    security = shutil.which("security")
    if not args.fixture_mode and (sys.platform != "darwin" or security is None):
        errors.append("macOS Keychain security CLI is unavailable")
    elif security:
        checks["keychain_cli"] = security
    mineru_cli = shutil.which("mineru-open-api")
    if not args.fixture_mode and mineru_cli is None:
        errors.append("official mineru-open-api CLI is unavailable")
    elif mineru_cli:
        checks["mineru_open_api_cli"] = mineru_cli
        if not args.fixture_mode:
            version = subprocess.run(
                [mineru_cli, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if version.returncode != 0:
                errors.append("mineru-open-api version check failed")
            else:
                checks["mineru_open_api_version"] = version.stdout.splitlines()[0].strip()

    token_file = args.token_file.resolve()
    if not token_file.is_file():
        questions.append({"id": "encrypted_token", "prompt": "尚未配置加密 MinerU token；现在运行 token-store.py set 吗？"})
    else:
        mode = token_file.stat().st_mode & 0o777
        checks["encrypted_token_file"] = str(token_file)
        checks["encrypted_token_mode"] = f"{mode:04o}"
        if mode != 0o600:
            errors.append(f"encrypted token file mode must be 0600, found {mode:04o}")
        if not args.fixture_mode:
            status = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent / "token-store.py"), "status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if status.returncode != 0:
                questions.append({
                    "id": "keychain_wrapping_key",
                    "prompt": "加密 token 的 Keychain wrapping key 不可用；请重新提供 token 以替换 credential state。",
                })

    result = {
        "ok": not errors and not questions,
        "errors": errors,
        "questions": questions,
        "checks": checks,
        "resolved": {
            "source": str(source),
            "course": args.course,
            "profile": args.profile,
            "language": None if args.language is None or args.language.lower() == "auto" else args.language,
            "is_ocr": None if args.is_ocr is None else args.is_ocr == "true",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
