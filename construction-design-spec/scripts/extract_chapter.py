#!/usr/bin/env python3
"""Extract a chapter from school_arch_template.md. Cross-platform replacement for grep/sed."""

import os
import sys
from pathlib import Path


def _normalize(s: str) -> str:
    """Normalize chapter name for matching: strip chapter numbers like '第X章', '1.', '1、' etc."""
    import re
    # Remove leading chapter/section patterns: 第X章, 第X节, X., X、, X#, X #
    s = re.sub(r"^第[一二三四五六七八九十百千0-9]+[章节部]\s*", "", s)
    s = re.sub(r"^[0-9]+[.、#\s]\s*", "", s)
    return s.strip()


def extract_chapter(text: str, chapter_name: str) -> str:
    """Extract a specific chapter from template text.

    Args:
        text: Full template text
        chapter_name: Chapter name to extract (fuzzy match, normalized)

    Returns:
        Extracted chapter content, or error message
    """
    lines = text.splitlines()

    # Normalize the search term
    norm_query = _normalize(chapter_name.lower())

    # Find chapter heading: lines starting with "# " or "## " (at start of line)
    chapter_start = -1
    chapter_end = len(lines)
    current_heading_level = 0
    found_heading = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match chapter headings like "# 1.设计依据" or "## 2.1 工程概况"
        if stripped.startswith("# ") or stripped.startswith("## "):
            heading_level = len(line) - len(line.lstrip("#"))
            heading_text = stripped.lstrip("# ").strip()
            # Normalize heading text for comparison
            norm_heading = _normalize(heading_text.lower())
            # Check if normalized query is contained in normalized heading
            if norm_query and norm_query in norm_heading:
                chapter_start = i
                current_heading_level = heading_level
                found_heading = heading_text
            elif chapter_start >= 0:
                # Stop only when hitting a heading at the SAME level or shallower
                if heading_level <= current_heading_level:
                    chapter_end = i
                    break

    if chapter_start < 0:
        return f"Error: Chapter not found: {chapter_name}"

    chapter_lines = lines[chapter_start:chapter_end]
    return "\n".join(chapter_lines)


def resolve_input_path(raw_path: str | Path, invocation_cwd: Path, skill_dir: Path) -> Path:
    candidate = Path(raw_path)
    candidates = []

    if candidate.is_absolute():
        candidates.append(candidate)
    else:
        candidates.extend(
            [
                invocation_cwd / candidate,
                skill_dir / candidate,
                candidate,
            ]
        )

    for item in candidates:
        resolved = item.resolve()
        if resolved.exists():
            return resolved

    return candidate.resolve()


if __name__ == "__main__":
    # Force UTF-8 I/O on Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    invocation_cwd = Path.cwd().resolve()

    # 自动检测 skill 根目录（脚本的上一级）
    skill_dir = Path(__file__).parent.resolve().parent
    os.chdir(skill_dir)

    template_path = None
    chapter_name = None

    # Read args from SCRIPT_ARGS env var (cross-platform Unicode-safe via environment)
    script_args = os.environ.get("SCRIPT_ARGS", "")
    if script_args:
        try:
            import json as _json
            parsed = _json.loads(script_args)
            template_path = parsed.get("template")
            chapter_name = parsed.get("chapter")
        except Exception:
            pass

    # Fall back to argv
    if not template_path or not chapter_name:
        if len(sys.argv) < 3:
            print("Usage: extract_chapter.py <template_path> <chapter_name>")
            print("   or: SCRIPT_ARGS='{\"template\":\"...\",\"chapter\":\"...\"}' python extract_chapter.py")
            sys.exit(1)
        template_path = Path(sys.argv[1])
        chapter_name = sys.argv[2]

    if not template_path or not chapter_name:
        print("Error: both template_path and chapter_name are required")
        sys.exit(1)

    template_path = resolve_input_path(template_path, invocation_cwd, skill_dir)

    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}")
        sys.exit(1)

    text = template_path.read_text(encoding="utf-8")
    result = extract_chapter(text, chapter_name)
    print(result)
