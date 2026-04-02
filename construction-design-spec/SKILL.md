---
name: construction-design-spec
description: |
  生成完整的建筑施工设计说明、建筑设计说明或施工图设计说明，适用于需要根据项目资料抽取信息、裁剪目录并逐章成稿的长流程任务。用户提到“生成整本设计说明”“根据任务书/方案/审图意见整理完整建筑说明”“输出完整建筑工程设计说明”时应使用本技能。若只需润色、翻译、补单章、补小节或回答单条规范问题，则不使用本技能。
compatibility: |
  需要 Bash 运行随附 Python 脚本
---

# 建筑施工设计说明文档生成

## 适用边界

- **使用本技能**：生成整本施工设计说明/建筑设计说明/施工图设计说明。
- **不要使用本技能**：润色、翻译、总结、补单章、补小节、回答单条规范问题。
- **单章节请求**：直接在当前上下文处理，不走整套流程。

## 核心规则

1. 先分流，再提取项目信息，再确认目录，再逐章生成，最后整文校验。
2. 模板中的占位符（如 `xxx`）应结合项目信息主动推理填充，不要留占位符。
3. 目录和章节优先用脚本提取，不手工抄模板。
4. 各章必须串行生成；上一章没过校验，不要开始下一章。

## 推荐中间产物

- `project_info.json`
- `outline_decision.md`
- `chapter_plan.json`
- `建筑施工设计说明_{项目名称}.md`

## 工作流

```text
Step 1: 项目信息提取
Step 2: 大纲确认与裁剪
Step 3: 逐章生成
Step 4: 整文校验与交付
```

## Step 1: 项目信息提取

读取 `references/project_info.md`，根据项目概要、任务书、方案文本、审图意见、地方要求等资料提取 `project_info.json`。

提取规则：

- 原文明确给出的参数直接提取。
- 涉及地方规范、审查口径、强条适用性的内容，如有依据则写，无依据则参考类似项目写法或合理推断，不要留任何占位符标记。
- 所有数值保留单位。

进入 Step 2 前至少确认：

- 项目名称
- 建设地点
- 建筑类型 / 使用功能
- 建筑面积、层数、高度
- 结构形式
- 是否涉及地下室、人防、幕墙、电梯、装配式、绿建等专项

## Step 2: 大纲确认与裁剪

先提取模板目录：

```bash
python ./scripts/extract_toc.py ./assets/public_building_template.md
```

或：

```bash
SCRIPT_ARGS='{"template":"./assets/public_building_template.md"}' python ./scripts/extract_toc.py
```

然后输出 `outline_decision.md`，列出：

- 保留章节
- 删除章节及原因
- 需人工核验的地区性或专项章节

裁剪规则：

- 通用章节通常保留。
- 人防、绿建、装配式、海绵城市、幕墙、电梯等按项目条件决定。
- 模板中的城市样例、地方审查要点只能参考；不适用时替换为本项目要求或合理推断，不要留占位符标记。
- 模板提示语不得进入最终正文。

用户确认目录后，再进入 Step 3。

## Step 3: 逐章生成

**每章必须独立执行完整流程，不得在所有章节规划完后再批量检索。RAGFlow 检索是强制步骤，不可跳过或伪造。**

使用 `chapter-generator` subagent 生成每章内容：

**Spawn chapter-generator subagent for each chapter** (详见 `agents/chapter-generator.md`)：

- 输入：chapter_name, project_info_path, output_dir, final_doc_path
- 输出：最终文档 `建筑施工设计说明_{项目名称}.md`（subagent 已处理所有步骤）
- **RAGFlow 检索失败 = 本章生成中断，提示用户企业知识库不可用**

## Step 4: 整文校验与交付

所有章节完成后，再按 `references/validation_checklist.md` 做整文校验：

1. 章节顺序与编号连续
2. 项目名称、地点、面积、高度、层数、结构形式前后一致
3. 同一参数未在不同章节出现冲突
4. 没有残留模板占位符、样例城市、样例项目名

交付时说明：

- 最终文档路径

## 参考文件

- `references/project_info.md`
- `references/validation_checklist.md`
- `assets/public_building_template.md`

优先执行：

- `scripts/extract_toc.py`
- `scripts/extract_chapter.py`
- `scripts/ragflow_query.py`

## 常见错误

| 错误 | 正确做法 |
|------|----------|
| 还没确认关键信息就开始写正文 | 先补齐项目关键字段 |
| 输出残留样例城市、样例项目名、模板提示语 | 每章生成后立即自检清洗 |
