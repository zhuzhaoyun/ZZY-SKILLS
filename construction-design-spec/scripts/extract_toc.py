#!/usr/bin/env python3
"""Extract table of contents (TOC) from school_arch_template.md.

Reads the template and outputs a tree-structured outline of all chapters
and subsections for user confirmation before document generation.
"""

import os
import re
import sys
from pathlib import Path


def extract_toc(text: str) -> str:
    """Extract all headings from template as a tree-structured TOC.

    Args:
        text: Full template text

    Returns:
        Tree-structured TOC string with chapter numbers and titles
    """
    lines = text.splitlines()
    toc_lines = []
    chapter_counter = {}

    for line in lines:
        stripped = line.strip()
        # Match markdown headings: #, ##, ###
        m = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if not m:
            continue

        level = len(m.group(1))  # 1, 2, or 3
        title = m.group(2).strip()

        if title.startswith("目录"):
            continue

        # Skip lines that are just noise (e.g. "附件1..." on line 1)
        if level == 1 and not re.search(r"[\d一二三四五六七八九十]", title[:4]):
            # Top-level heading without number prefix - include anyway
            pass

        indent = "  " * (level - 1)
        toc_lines.append(f"{indent}{title}")

    return "\n".join(toc_lines)


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
    out_path = None

    # Read args from SCRIPT_ARGS env var (cross-platform Unicode-safe via environment)
    script_args = os.environ.get("SCRIPT_ARGS", "")
    if script_args:
        try:
            import json as _json
            parsed = _json.loads(script_args)
            template_path = parsed.get("template")
            out_path = parsed.get("out_path")
        except Exception:
            pass

    # Fall back to argv
    if not template_path:
        if len(sys.argv) < 2:
            print("Usage: extract_toc.py <template_path>")
            print("   or: SCRIPT_ARGS='{\"template\":\"...\"}' python extract_toc.py")
            sys.exit(1)
        template_path = Path(sys.argv[1])
        out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    if not template_path:
        print("Error: template_path is required", file=sys.stderr)
        sys.exit(1)

    template_path = resolve_input_path(template_path, invocation_cwd, skill_dir)

    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    text = template_path.read_text(encoding="utf-8")
    result = extract_toc(text)

    if out_path:
        Path(out_path).write_text(result, encoding="utf-8")
    print(result)
