#!/usr/bin/env python3
"""Plan content-driven lecture notes from normalized MinerU page groups.

This script owns the *skeleton*, not the prose. It turns MinerU page groups into a
draft note plan plus a draft page ledger, and it validates the Agent's finalized
versions of both. The Agent reads the source visually, finalizes the plan and the
ledger, and then writes the notes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path


PROFILE = "lecture-notes"
GRANULARITIES = ("single-note", "section-notes")
DROP_REASONS = {
    "title-slide", "section-divider", "agenda", "course-admin", "exercise",
    "repeated-chrome", "page-furniture", "duplicate", "illegible", "non-substantive",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# Section notes must carry a two-digit source-order ordinal so a plain filename sort
# still matches the order of the source document.
SECTION_ORDINAL = re.compile(r"(?:^|-)(\d{2})(?:-|$)")
ASSET_FILE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(?:png|jpg|jpeg|webp|gif|bmp|svg)$")
NUMBERED = re.compile(r"^\s*(?:(\d{1,2}(?:\.\d{1,2})*)|([A-Z]))\s*[.、)]?\s+(\S.*)$")
CJK = re.compile(r"[\u3400-\u9fff]")
ADMIN_HINTS = re.compile(
    r"(?:invitation code|\u9080\u8bf7\u7801|course information|\u8bfe\u7a0b\u4fe1\u606f|"
    r"office|teacher|instructor|@\w+\.\w+|zoom|teams meeting)",
    re.I,
)
EXERCISE_HINTS = re.compile(
    r"(?:\u4e60\u9898|\u7ec3\u4e60|quiz|exercise|exam|homework|question\s*\d)",
    re.I,
)
VISUAL_TYPES = {"image", "chart", "table"}
# Why a visual may be dropped. "repeated-chrome" is detected deterministically by the
# planner; the rest are Agent judgements that must be stated explicitly.
# Drop reasons that assert a page carried no substantive content. A page that holds a
# detected visual may not use these: that combination is how an image-only slide gets
# triaged away by a text-based judgement.
CONTENT_ASSERTING_DROP_REASONS = {
    "title-slide", "section-divider", "agenda", "course-admin", "exercise", "non-substantive",
}
VISUAL_DROP_REASONS = {
    "repeated-chrome",      # logo, crest, watermark, template ornament, footer bar
    "decorative",           # clipart, stock imagery, ornament carrying no information
    "redundant-with-text",  # a diagram whose content the surrounding text fully states
    "duplicate",            # the same visual is already kept elsewhere
    "illegible",            # unreadable scan or unrenderable image
    "superseded-by-table",  # replaced by a Markdown table; requires rendered_as
}

# A visual block whose position and size recur on at least this share of pages is
# template chrome rather than page content.
CHROME_PAGE_SHARE = 0.5
CHROME_MIN_PAGES = 3
AUX_TYPES = {"page_header", "page_footer", "page_number", "page_aside_text", "page_footnote"}


class PlanError(RuntimeError):
    pass


def flatten(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "".join(flatten(item) for item in value)
    if isinstance(value, dict):
        if isinstance(value.get("content"), str):
            return value["content"]
        preferred = [
            "title_content", "paragraph_content", "math_content", "code_content",
            "algorithm_content", "list_items", "image_caption", "table_caption",
            "chart_caption", "page_header_content", "page_footer_content",
            "page_footnote_content",
        ]
        for key in preferred:
            if key in value:
                return flatten(value[key])
        return "".join(flatten(item) for item in value.values())
    return ""


def page_blocks(page) -> list[dict]:
    if isinstance(page, list):
        return [item for item in page if isinstance(item, dict)]
    if isinstance(page, dict):
        for key in ("blocks", "content", "items"):
            if isinstance(page.get(key), list):
                return [item for item in page[key] if isinstance(item, dict)]
        raise PlanError("each normalized page must be an array or page object with blocks")
    raise PlanError("each normalized page must be an array or page object with blocks")


def normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[\s\u3000]+", " ", text)
    text = re.sub(r"^(?:\d+(?:\.\d+)*|[a-d])[\s.、)]+", "", text)
    text = re.sub(r"[\s:：\-—–_.,，、()（）\[\]【】'\"“”]+$", "", text)
    return text


def as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_number(value) -> str:
    try:
        return f"{round(float(value), 3):g}"
    except (TypeError, ValueError):
        return str(value)


def visual_signature(block: dict) -> str:
    """Identify a visual block by footprint so repeated template art collapses to one key."""
    bbox = block.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        numbers = [value for value in bbox if isinstance(value, (int, float))]
        if len(numbers) == 4:
            # Normalized (0..1) and absolute coordinates both round to a stable key.
            parts = [format_number(value) for value in numbers]
            return "bbox:" + ",".join(parts)
    return f"type:{block.get('type')}"


def chrome_signatures(signals: list[dict]) -> set[str]:
    """Visual footprints that repeat across the deck are template chrome, not content."""
    counts: dict[str, int] = {}
    for item in signals:
        for signature in set(item.get("visual_signatures", [])):
            counts[signature] = counts.get(signature, 0) + 1
    if not signals:
        return set()
    threshold = max(CHROME_MIN_PAGES, round(len(signals) * CHROME_PAGE_SHARE))
    return {signature for signature, count in counts.items() if count >= threshold}


def page_signals(index: int, page) -> dict:
    blocks = [block for block in page_blocks(page) if block.get("type") not in AUX_TYPES]
    titles: list[str] = []
    body_parts: list[str] = []
    visual_types: list[str] = []
    visual_signatures: list[str] = []
    visual_count = 0
    for block in blocks:
        block_type = block.get("type")
        text = flatten(block.get("content")).strip()
        if block_type == "title":
            if text:
                titles.append(text)
            continue
        if block_type in VISUAL_TYPES:
            visual_count += 1
            visual_types.append(block_type)
            visual_signatures.append(visual_signature(block))
        if text:
            body_parts.append(text)
    body = "\n".join(body_parts)
    numbered = [title for title in titles if NUMBERED.match(title)]
    numbered += [line for line in body.splitlines() if NUMBERED.match(line) and len(line) <= 90]
    return {
        "page": index + 1,
        "titles": titles,
        "first_title": titles[0] if titles else "",
        "block_count": len(blocks),
        "char_count": len(body) + sum(len(title) for title in titles),
        "visual_count": visual_count,
        "visual_types": visual_types,
        "visual_signatures": visual_signatures,
        "body": body,
        "numbered": numbered,
        "divider_like": len(blocks) <= 3 and len(body) < 140 and visual_count == 0,
    }


def section_entries(signals: list[dict]) -> tuple[int, list[str]] | None:
    best: tuple[int, list[str]] | None = None
    for item in signals:
        entries = item["numbered"]
        if len(entries) < 3:
            continue
        unique = []
        for entry in entries:
            text = entry.strip()
            if text and text not in unique:
                unique.append(text)
        if best is None or len(unique) > len(best[1]):
            best = (item["page"], unique)
    return best


def draft_sections(signals: list[dict], outline: tuple[int, list[str]] | None) -> list[dict]:
    if outline is not None:
        outline_page, entries = outline
        starts: list[int] = []
        cursor = outline_page
        for entry in entries:
            target = normalize_text(entry)
            found = None
            for item in signals:
                if item["page"] <= cursor:
                    continue
                if normalize_text(item["first_title"]) == target:
                    found = item["page"]
                    break
            starts.append(found if found is not None else cursor + 1)
            cursor = starts[-1]
        sections = []
        for position, entry in enumerate(entries):
            start = starts[position]
            end = starts[position + 1] - 1 if position + 1 < len(starts) else len(signals)
            end = max(end, start)
            pages = [value for value in range(start, end + 1) if value <= len(signals)]
            sections.append({"heading": entry.strip(), "pages": pages, "subtopics": []})
        leading = [value for value in range(1, starts[0]) if value != outline_page]
        if sections and leading:
            sections[0]["pages"] = sorted(set(leading + sections[0]["pages"]))
        return sections

    sections = []
    for item in signals:
        if item["divider_like"] or not item["first_title"]:
            continue
        heading = item["first_title"].strip()
        if not heading:
            continue
        if sections and sections[-1]["heading"] == heading:
            continue
        sections.append({"heading": heading, "pages": [item["page"]], "subtopics": []})
    if not sections:
        sections = [{"heading": "Content", "pages": [item["page"] for item in signals], "subtopics": []}]
    for position, section in enumerate(sections):
        start = section["pages"][0]
        end = sections[position + 1]["pages"][0] - 1 if position + 1 < len(sections) else len(signals)
        section["pages"] = [value for value in range(start, max(end, start) + 1) if value <= len(signals)]
    return sections


def recommend_granularity(granularity_entries: int, source_pages: int) -> str:
    if granularity_entries >= 3 and source_pages >= 60:
        return "section-notes"
    return "single-note"


def draft_ledger(signals: list[dict], note_slug: str, sections: list[dict]) -> dict:
    chrome = chrome_signatures(signals)
    owner: dict[int, str] = {}
    for section in sections:
        for page in section["pages"]:
            if isinstance(page, int):
                owner[page] = section["heading"]
    pages = []
    for index, item in enumerate(signals):
        page = item["page"]
        reason = ""
        if page == 1 and len(signals) > 3:
            reason = "title-slide"
        elif ADMIN_HINTS.search(item["body"] + " " + " ".join(item["titles"])):
            reason = "course-admin"
        elif EXERCISE_HINTS.search(item["first_title"]):
            reason = "exercise"
        elif item["divider_like"] and normalize_text(item["first_title"]) in {
            normalize_text(section["heading"]) for section in sections
        }:
            reason = "section-divider"
        elif not item["titles"] and not item["body"].strip() and item["visual_count"] == 0:
            reason = "page-furniture"
        if reason:
            pages.append({"page": page, "disposition": "dropped", "reason": reason})
        else:
            pages.append({
                "page": page,
                "disposition": "kept",
                "note": note_slug,
                "section": owner.get(page, sections[0]["heading"] if sections else ""),
                "evidence": "",
                # Extracting a detected visual is the default; the Agent names it, or
                # declares a controlled drop reason. Repeated template chrome is already
                # classified here so a logo does not have to be dismissed page by page.
                "visuals": [
                    (
                        {"disposition": "dropped", "reason": "repeated-chrome"}
                        if signature in chrome
                        else {"disposition": "kept", "asset": "", "kind": kind}
                    )
                    for kind, signature in zip(item["visual_types"], item["visual_signatures"])
                ],
            })
    return {
        "schema_version": 1,
        "draft": True,
        "source_pages": len(signals),
        "detected_repeated_chrome": len(chrome),
        "pages": pages,
    }


def build_plan_from_page_count(
    page_count: int, granularity: str, slug: str, title: str
) -> tuple[dict, dict]:
    """Native multimodal planning: no MinerU page groups, the Agent authors the skeleton."""
    if not isinstance(page_count, int) or page_count <= 0:
        raise PlanError("page count must be a positive integer")
    if granularity not in GRANULARITIES:
        raise PlanError(f"granularity must be one of {', '.join(GRANULARITIES)}")
    if not SLUG.fullmatch(slug):
        raise PlanError("slug must be lowercase kebab-case")
    plan = {
        "schema_version": 1,
        "profile": PROFILE,
        "granularity": granularity,
        "source_pages": page_count,
        "draft": True,
        "notes": [{"slug": slug, "title": title, "sections": []}],
        "_signals": {
            "page_signals": [],
            "granularity_recommendation": recommend_granularity(0, page_count),
            "instructions": [
                "No MinerU page groups were supplied, so nothing was inferred from a text layer.",
                "Read the source natively, page by page, and author the section list yourself.",
                "Section headings follow the source document's own outline, never slide numbers.",
                "Give every section the source pages it draws on.",
                "Record one evidence phrase per kept page and mark furniture pages as dropped.",
                "List every visual you saw on each kept page in visuals[]: extracted with an asset name, or dropped with a controlled reason.",
                "Never describe a visual in prose and drop it; extract it and embed it where it belongs.",
                "Set draft=false on both the plan and the ledger when they are final.",
            ],
        },
    }
    ledger = {
        "schema_version": 1,
        "draft": True,
        "source_pages": page_count,
        "pages": [
            {"page": page, "disposition": "kept", "note": slug, "section": "", "evidence": "", "visuals": []}
            for page in range(1, page_count + 1)
        ],
    }
    return plan, ledger


def slugify(text: str, fallback: str, maximum: int = 40) -> str:
    """ASCII kebab-case for a heading, falling back when the heading is not Latin."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", ascii_text.lower())
    slug = "-".join(tokens)[:maximum].strip("-")
    return slug or fallback


def section_note_slug(document_slug: str, index: int, heading: str) -> str:
    """<document>-<NN>-<section>, so the ordinal keeps source order in a file listing.

    The heading's own numbering is stripped first: the ordinal already encodes order,
    and keeping both produced names like `course-01-1-introduction`.
    """
    # The separator is required: without it a heading like "Content" loses its "C"
    # to the [A-D] list-marker alternative.
    cleaned = re.sub(r"^\s*(?:\d+(?:\.\d+)*|[A-D])[\s.、)、)]+", "", heading)
    return f"{document_slug}-{index + 1:02d}-{slugify(cleaned, 'section')}"


def build_plan(pages: list, profile: str, granularity: str, slug: str, title: str) -> tuple[dict, dict]:
    if profile != PROFILE:
        raise PlanError(
            f"plan-note-structure.py only plans the {PROFILE} profile; "
            "use reconstruct-note.py for a MinerU-based policy-document or paper transcription"
        )
    if granularity not in GRANULARITIES:
        raise PlanError(f"granularity must be one of {', '.join(GRANULARITIES)}")
    if not SLUG.fullmatch(slug):
        raise PlanError("slug must be lowercase kebab-case")
    if not isinstance(pages, list) or not pages:
        raise PlanError("page-group input must be a non-empty top-level array")
    signals = [page_signals(index, page) for index, page in enumerate(pages)]
    outline = section_entries(signals)
    sections = draft_sections(signals, outline)
    if granularity == "section-notes":
        notes = [
            {
                "slug": section_note_slug(slug, index, section["heading"]),
                "title": section["heading"],
                "sections": [{"heading": section["heading"], "pages": section["pages"], "subtopics": []}],
            }
            for index, section in enumerate(sections)
        ]
    else:
        notes = [{"slug": slug, "title": title, "sections": sections}]
    plan = {
        "schema_version": 1,
        "profile": PROFILE,
        "granularity": granularity,
        "source_pages": len(signals),
        "draft": True,
        "notes": notes,
        "_signals": {
            "outline_page": outline[0] if outline else None,
            "outline_entries": outline[1] if outline else [],
            "suggested_section_count": len(sections),
            # Image-only pages carry their content in a figure, so a text-based triage
            # misreads them as empty. The Agent must resolve each one explicitly.
            "image_only_pages": [
                item["page"] for item in signals
                if item["visual_count"] > 0 and item["char_count"] < 45
            ],
            "granularity_recommendation": recommend_granularity(len(sections), len(signals)),
            "page_signals": signals,
            "instructions": [
                "Read the source visually and correct this draft before writing any note.",
                "Section headings are content headings, never slide titles or slide numbers.",
                "Drop agenda, divider, course-admin, exercise, and page-furniture pages in the ledger.",
                "A page whose content is a figure or a wide data table is a content page, not furniture.",
                "Check _signals.image_only_pages by hand before dropping any of them.",
                "Set draft=false on both the plan and the ledger when they are final.",
            ],
        },
    }
    ledger = draft_ledger(signals, notes[0]["slug"], sections)
    return plan, ledger


def validate_plan(plan: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        return ["note plan must be an object with schema_version 1"]
    if plan.get("draft", True):
        errors.append("note plan is still a draft; set draft=false after reviewing the source visually")
    if plan.get("profile") != PROFILE:
        errors.append(f"note plan profile must be {PROFILE}")
    if plan.get("granularity") not in GRANULARITIES:
        errors.append(f"note plan granularity must be one of {', '.join(GRANULARITIES)}")
    try:
        source_pages = int(plan.get("source_pages", 0))
    except (TypeError, ValueError):
        source_pages = 0
    if source_pages <= 0:
        errors.append("note plan source_pages must be a positive integer")
    notes = plan.get("notes")
    if not isinstance(notes, list) or not notes:
        errors.append("note plan must declare at least one note")
        return errors
    if plan.get("granularity") == "single-note" and len(notes) != 1:
        errors.append("single-note granularity must declare exactly one note")
    if plan.get("granularity") == "section-notes" and len(notes) < 2:
        errors.append("section-notes granularity must declare two or more notes")
    slugs: set[str] = set()
    section_notes = plan.get("granularity") == "section-notes"
    ordinals: list[int] = []
    pages_seen: list[int] = []
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append(f"notes[{index}] must be an object")
            continue
        slug = note.get("slug")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in slugs:
            errors.append(f"notes[{index}].slug must be a unique lowercase kebab-case slug")
        else:
            slugs.add(slug)
        if section_notes and isinstance(slug, str):
            ordinal = SECTION_ORDINAL.search(slug)
            if ordinal is None:
                errors.append(
                    f"notes[{index}].slug must carry a two-digit source-order ordinal, "
                    f"as in <document>-01-<section>: {slug!r}"
                )
            else:
                ordinals.append(as_int(ordinal.group(1)))
        title = note.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"notes[{index}].title must be non-empty text")
            continue
        sections = note.get("sections")
        if not isinstance(sections, list) or not sections:
            errors.append(f"notes[{index}] must declare at least one content section")
            continue
        headings: set[str] = set()
        for position, section in enumerate(sections):
            label = f"notes[{index}].sections[{position}]"
            if not isinstance(section, dict):
                errors.append(f"{label} must be an object")
                continue
            heading = section.get("heading")
            if not isinstance(heading, str) or not heading.strip():
                errors.append(f"{label}.heading must be non-empty text")
                continue
            if heading in headings:
                errors.append(f"{label}.heading duplicates another section in the same note: {heading!r}")
            headings.add(heading)
            if isinstance(heading, str) and (
                re.match(r"^\s*(?:slide|page)\s*\d+", heading, re.I)
                or re.fullmatch(r"\d+", heading.strip())
            ):
                errors.append(f"{label}.heading looks like slide furniture, not a content heading: {heading!r}")
            section_pages = section.get("pages")
            if not isinstance(section_pages, list) or not section_pages:
                errors.append(f"{label}.pages must list at least one source page")
                continue
            for page in section_pages:
                if not isinstance(page, int) or page < 1 or (source_pages and page > source_pages):
                    errors.append(f"{label}.pages contains an invalid page: {page!r}")
            numeric_pages = [page for page in section_pages if isinstance(page, int)]
            if numeric_pages:
                pages_seen.append(min(numeric_pages))
    if section_notes and ordinals:
        expected = list(range(1, len(notes) + 1))
        if ordinals != expected:
            errors.append(
                f"section-note ordinals must be 01..{len(notes):02d} in source order: {ordinals}"
            )
    if section_notes and len(pages_seen) == len(notes) and pages_seen != sorted(pages_seen):
        errors.append(
            "section notes must be listed in source page order: "
            + ", ".join(str(page) for page in pages_seen)
        )
    return errors


def validate_page_visuals(page: int, visuals) -> list[str]:
    """Every kept page declares what happened to each visual it carries."""
    errors: list[str] = []
    if not isinstance(visuals, list):
        return [
            f"page {page} must declare visuals[] (use [] only when the page carries no visual); "
            "summarizing a visual in prose and dropping it is not allowed"
        ]
    for index, entry in enumerate(visuals):
        label = f"page {page} visuals[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} must be an object")
            continue
        disposition = entry.get("disposition")
        if disposition == "kept":
            asset = entry.get("asset")
            if not isinstance(asset, str) or not asset.strip():
                errors.append(
                    f"{label} is kept but names no asset; extract it, name it, and embed it at its "
                    "point of use"
                )
            elif not ASSET_FILE.fullmatch(asset.strip()):
                errors.append(
                    f"{label}.asset must be a lowercase semantic kebab-case filename: {asset!r}"
                )
        elif disposition == "dropped":
            reason = entry.get("reason")
            if reason not in VISUAL_DROP_REASONS:
                errors.append(
                    f"{label} is dropped without a supported reason: {reason!r}; "
                    f"allowed={sorted(VISUAL_DROP_REASONS)}"
                )
            elif reason == "superseded-by-table" and entry.get("rendered_as") != "markdown-table":
                errors.append(
                    f"{label} claims superseded-by-table but does not state "
                    "rendered_as: \"markdown-table\""
                )
        else:
            errors.append(f"{label} has an unsupported disposition: {disposition!r}")
    return errors


def validate_ledger(ledger: dict, plan: dict, allow_heavy_drop: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1:
        return ["page ledger must be an object with schema_version 1"]
    if ledger.get("draft", True):
        errors.append("page ledger is still a draft; set draft=false after reviewing the source visually")
    try:
        source_pages = int(ledger.get("source_pages", 0))
    except (TypeError, ValueError):
        source_pages = 0
    if source_pages <= 0:
        errors.append("page ledger source_pages must be a positive integer")
    plan_sections: dict[str, set[str]] = {}
    for note in plan.get("notes", []) if isinstance(plan, dict) else []:
        if isinstance(note, dict) and isinstance(note.get("slug"), str):
            plan_sections[note["slug"]] = {
                section["heading"]
                for section in note.get("sections", [])
                if isinstance(section, dict) and isinstance(section.get("heading"), str)
            }
    pages = ledger.get("pages")
    if not isinstance(pages, list) or not pages:
        errors.append("page ledger must list every source page")
        return errors
    # Page signals are an optional, MinerU-only aid; when present they make the
    # image-only-page rule mechanically checkable.
    detected_visuals: dict[int, int] = {}
    signals = plan.get("_signals", {}).get("page_signals", []) if isinstance(plan, dict) else []
    if isinstance(signals, list):
        for signal in signals:
            if isinstance(signal, dict) and isinstance(signal.get("page"), int):
                count = signal.get("visual_count")
                if isinstance(count, int) and count > 0:
                    detected_visuals[signal["page"]] = count
    seen: dict[int, dict] = {}
    dropped = 0
    for index, item in enumerate(pages):
        if not isinstance(item, dict):
            errors.append(f"pages[{index}] must be an object")
            continue
        page = item.get("page")
        if not isinstance(page, int) or page < 1 or (source_pages and page > source_pages):
            errors.append(f"pages[{index}].page is invalid: {page!r}")
            continue
        if page in seen:
            errors.append(f"page {page} is listed more than once in the ledger")
        seen[page] = item
        disposition = item.get("disposition")
        if disposition not in {"kept", "merged", "dropped"}:
            errors.append(f"page {page} has an unsupported disposition: {disposition!r}")
            continue
        if disposition == "dropped":
            dropped += 1
            reason = item.get("reason")
            detected = detected_visuals.get(page)
            if detected and reason in CONTENT_ASSERTING_DROP_REASONS:
                errors.append(
                    f"page {page} carries {detected} detected visual(s) but is dropped as "
                    f"{reason!r}, which asserts the page had no content; keep the page and "
                    "extract its figure, or drop it for a visual-aware reason such as "
                    "duplicate, repeated-chrome, or illegible"
                )
            if reason not in DROP_REASONS:
                errors.append(
                    f"page {page} is dropped without a supported reason: {reason!r}; "
                    f"allowed={sorted(DROP_REASONS)}"
                )
            continue
        note_slug = item.get("note")
        if note_slug not in plan_sections:
            errors.append(f"page {page} maps to an unknown note slug: {note_slug!r}")
            continue
        section = item.get("section")
        if section not in plan_sections[note_slug]:
            errors.append(f"page {page} maps to an unknown section of {note_slug}: {section!r}")
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not 8 <= len(evidence.strip()) <= 200:
            errors.append(
                f"page {page} needs an 8..200 character evidence phrase quoted from its target note"
            )
        errors += validate_page_visuals(page, item.get("visuals"))
    if source_pages:
        missing = [page for page in range(1, source_pages + 1) if page not in seen]
        if missing:
            errors.append("page ledger is missing source pages: " + ", ".join(str(page) for page in missing[:20]))
    if source_pages and not allow_heavy_drop and dropped > source_pages / 2:
        errors.append(
            f"page ledger drops {dropped} of {source_pages} pages; "
            "pass --allow-heavy-drop after confirming the source is mostly furniture"
        )
    return errors


def write_json_atomic(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-groups", "--content-list-v2", dest="page_groups", type=Path)
    parser.add_argument("--page-count", type=int, help="Source page count for native multimodal planning")
    parser.add_argument("--profile", required=True, choices=("lecture-notes", "policy-document", "paper"))
    parser.add_argument("--granularity", required=True, choices=GRANULARITIES)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ledger-output", required=True, type=Path)
    parser.add_argument("--allow-heavy-drop", action="store_true")
    parser.add_argument("--check-plan", type=Path, help="Validate an existing finalized plan instead of drafting")
    parser.add_argument("--check-ledger", type=Path, help="Validate an existing finalized ledger instead of drafting")
    args = parser.parse_args()

    errors: list[str] = []
    payload: dict = {}
    try:
        if args.check_plan is not None or args.check_ledger is not None:
            plan = json.loads((args.check_plan or args.output).read_text(encoding="utf-8"))
            ledger = json.loads((args.check_ledger or args.ledger_output).read_text(encoding="utf-8"))
            errors += validate_plan(plan)
            errors += validate_ledger(ledger, plan, args.allow_heavy_drop)
            payload = {"valid": not errors, "errors": errors}
        elif args.page_groups is not None:
            pages = json.loads(args.page_groups.read_text(encoding="utf-8"))
            plan, ledger = build_plan(pages, args.profile, args.granularity, args.slug, args.title)
            write_json_atomic(args.output, plan)
            write_json_atomic(args.ledger_output, ledger)
            payload = {
                "plan": str(args.output),
                "ledger": str(args.ledger_output),
                "granularity": plan["granularity"],
                "source_pages": plan["source_pages"],
                "draft_note_count": len(plan["notes"]),
                "draft_sections": [
                    {"heading": section["heading"], "pages": section["pages"]}
                    for section in plan["notes"][0]["sections"]
                ],
                "granularity_recommendation": plan["_signals"]["granularity_recommendation"],
                "next": "read the source visually, correct both drafts, then set draft=false",
            }
        else:
            if args.page_count is None:
                raise PlanError("pass --page-count (native multimodal) or --page-groups (MinerU)")
            plan, ledger = build_plan_from_page_count(
                args.page_count, args.granularity, args.slug, args.title
            )
            write_json_atomic(args.output, plan)
            write_json_atomic(args.ledger_output, ledger)
            payload = {
                "plan": str(args.output),
                "ledger": str(args.ledger_output),
                "granularity": plan["granularity"],
                "source_pages": plan["source_pages"],
                "draft_note_count": len(plan["notes"]),
                "page_groups_available": False,
                "next": (
                    "read the source natively, author the sections and per-page evidence, "
                    "then set draft=false on both files"
                ),
            }
    except (OSError, json.JSONDecodeError, PlanError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
