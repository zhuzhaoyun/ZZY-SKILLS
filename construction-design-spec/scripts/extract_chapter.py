#!/usr/bin/env python3
"""
从 public_building_template.md 中提取指定章节的完整内容。

用法：
    python extract_chapter.py "21.节能设计"
    python extract_chapter.py "2.工程概况"
    SCRIPT_ARGS='{"chapter":"21.节能设计","template":"./assets/public_building_template.md"}' python extract_chapter.py

参数：
    chapter - 章节名称（支持模糊匹配，如 "21.节能" 或 "节能设计"）
    template - 模板文件路径（默认：./assets/public_building_template.md）
"""

import json
import os
import re
import sys
from pathlib import Path


def extract_chapter(chapter_name: str, template_path: str) -> str:
    """从模板中提取指定章节的完整内容。"""

    if not os.path.exists(template_path):
        return f"[错误] 模板文件不存在: {template_path}"

    with open(template_path, encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    start_idx = None
    chapter_title = None

    # 提取搜索关键词（去掉可能的冒号和前缀）
    # 用户可能输入 "21.节能设计" 或 "节能设计"，统一处理
    search_keywords = chapter_name.split('：')[0].split(':')[0].strip()
    # 如果输入包含数字.前缀，去掉它
    if re.match(r'^\d+\.', search_keywords):
        search_keywords = re.sub(r'^\d+\.', '', search_keywords)

    for i, line in enumerate(lines):
        stripped = line.strip()
        # 顶级章节以 # 开头，后面是数字和点
        if stripped.startswith('# '):
            # 提取章节名部分（去掉开头的 # 数字.）
            match = re.match(r'^#\s+\d+\.(.+?)\s*[:：]?\s*$', stripped)
            if match:
                section_name = match.group(1).strip()
                # 检查是否包含搜索关键词（模糊匹配）
                if search_keywords in section_name or section_name.startswith(search_keywords):
                    start_idx = i
                    chapter_title = stripped
                    break

    if start_idx is None:
        return f"[错误] 未找到章节: {chapter_name}"

    # 找到下一个顶级章节（以 # [数字]. 开头）
    end_idx = len(lines)
    next_chapter_pattern = re.compile(r'^#\s+\d+\.')

    for i in range(start_idx + 1, len(lines)):
        if next_chapter_pattern.match(lines[i]):
            end_idx = i
            break

    # 提取章节内容
    chapter_lines = lines[start_idx:end_idx]
    chapter_content = '\n'.join(chapter_lines)

    return chapter_content


def main():
    # 支持命令行参数和 SCRIPT_ARGS 环境变量
    script_args = os.environ.get('SCRIPT_ARGS', '{}')
    try:
        args = json.loads(script_args)
    except json.JSONDecodeError:
        args = {}

    # 命令行参数优先
    if len(sys.argv) > 1:
        args['chapter'] = sys.argv[1]
    if len(sys.argv) > 2:
        args['template'] = sys.argv[2]

    chapter = args.get('chapter', '')
    template = args.get('template', './assets/public_building_template.md')

    if not chapter:
        print("[错误] 请提供章节名称")
        print(__doc__)
        sys.exit(1)

    # 如果模板路径是相对路径，尝试相对于脚本目录
    if not os.path.isabs(template):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, '..', template)
        template_path = os.path.normpath(template_path)
    else:
        template_path = template

    result = extract_chapter(chapter, template_path)
    print(result)


if __name__ == '__main__':
    main()
