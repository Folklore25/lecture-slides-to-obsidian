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
GRANULARITIES = {"single-note", "section-notes"}
SYNTHESIS_PROFILE = "lecture-notes"
REQUIRED_SKILLS = {"obsidian-markdown", "obsidian-canvas-designer"}
MINERU_LANGUAGES = {
    "ch", "ch_server", "en", "japan", "korean", "chinese_cht", "ta",
    "te", "ka", "el", "th", "latin", "arabic", "cyrillic",
    "east_slavic", "devanagari",
}
POLICY_HINTS = re.compile(r"(?:policy|code[-_ ]of[-_ ]conduct|regulation|handbook|guideline|rules?)", re.IGNORECASE)
PAPER_HINTS = re.compile(r"(?:paper|article|thesis|dissertation|journal)", re.IGNORECASE)


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
    parser.add_argument("--note-granularity", choices=sorted(GRANULARITIES))
    parser.add_argument(
        "--extraction", choices=("native", "mineru"), default="native",
        help="native: the multimodal model reads the source directly (default). "
             "mineru: use the official MinerU CLI as an extraction aid.",
    )
    parser.add_argument("--confirm-profile-mismatch", action="store_true")
    parser.add_argument("--language")
    parser.add_argument("--is-ocr", choices=("true", "false"))
    parser.add_argument("--loaded-skill", action="append", default=[])
    parser.add_argument(
        "--visual-input", choices=("true", "false"),
        help="Whether the current model can view the source PDF or rendered page images.",
    )
    parser.add_argument("--latex-refinement", action="store_true")
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
        if args.extraction == "mineru" and source.stat().st_size > MAX_BYTES:
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

    synthesis_profile = args.profile == SYNTHESIS_PROFILE
    extraction = args.extraction
    native_extraction = extraction == "native"
    checks["extraction"] = extraction
    checks["content_driven_synthesis"] = synthesis_profile
    checks["mineru_available_but_optional"] = shutil.which("mineru-open-api") is not None
    granularity_required = args.profile in (None, SYNTHESIS_PROFILE)
    if args.note_granularity:
        checks["note_granularity"] = args.note_granularity
        if args.note_granularity == "section-notes" and not synthesis_profile:
            errors.append("section-notes granularity is only supported for the lecture-notes profile")
    elif granularity_required:
        questions.append({
            "id": "note_granularity",
            "prompt": (
                "笔记粒度必须由用户决定，不能默认：single-note（整份文档一篇笔记，源文档的节作为 H2）"
                "或 section-notes（源文档每个节一篇笔记）。读完源文档大纲后给出建议并让用户选择。"
            ),
        })

    if extraction == "mineru":
        if args.language is None or args.language.lower() == "auto":
            questions.append({"id": "language", "prompt": "请确认 MinerU language（例如纯英文用 en，中英混合用 ch）。"})
        elif args.language not in MINERU_LANGUAGES:
            errors.append(f"unsupported MinerU language enum: {args.language}")
        if args.is_ocr is None:
            questions.append({"id": "is_ocr", "prompt": "是否启用 OCR？请明确回答 true 或 false。"})
    else:
        checks["language"] = "not-applicable"
        checks["is_ocr"] = "not-applicable"

    loaded = set(args.loaded_skill)
    missing_skills = sorted(REQUIRED_SKILLS - loaded)
    if missing_skills:
        errors.append("helper skills not loaded through the Skill tool: " + ", ".join(missing_skills))
    checks["loaded_helper_skills"] = sorted(loaded & REQUIRED_SKILLS)
    checks["loaded_optional_skills"] = sorted(loaded & {"obsidian-latex-refiner"})

    if native_extraction:
        if args.visual_input is None:
            questions.append({
                "id": "native_visual_input",
                "prompt": (
                    "原生多模态转换必须由能直接看图的原生多模态模型完成："
                    "当前模型能否直接查看原 PDF 或逐页渲染图？请回答 true。"
                ),
            })
        elif args.visual_input != "true":
            errors.append(
                "native extraction requires a natively multimodal model with direct PDF or "
                "rendered page-image input; otherwise re-run with --extraction mineru"
            )
        else:
            checks["native_visual_input"] = True

    checks["latex_refinement"] = args.latex_refinement
    if args.latex_refinement and "obsidian-latex-refiner" not in loaded:
        errors.append("optional obsidian-latex-refiner skill was enabled but not loaded")

    obsidian_cli = shutil.which("obsidian")
    if not args.fixture_mode and obsidian_cli is None:
        errors.append("Obsidian CLI is unavailable for renderer QA")
    elif obsidian_cli:
        checks["obsidian_cli"] = obsidian_cli
        # Deliberately no version probe: presence on PATH is all the Canvas DOM
        # measurement step requires, and no gate consumes the version string.

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
    if extraction == "mineru" and not args.fixture_mode and mineru_cli is None:
        errors.append("official mineru-open-api CLI is unavailable")
    elif mineru_cli and extraction == "mineru":
        checks["mineru_open_api_cli"] = mineru_cli
        if not args.fixture_mode:
            version = subprocess.run(
                [mineru_cli, "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if version.returncode != 0:
                errors.append("mineru-open-api version check failed")
            else:
                checks["mineru_open_api_version"] = version.stdout.splitlines()[0].strip()

    token_file = args.token_file.resolve()
    if extraction != "mineru":
        checks["mineru_token"] = "not-required"  # noqa: S105 - a status marker, not a secret
    elif not token_file.is_file():
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
                capture_output=True,
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
            "note_granularity": args.note_granularity,
            "extraction": args.extraction,
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
