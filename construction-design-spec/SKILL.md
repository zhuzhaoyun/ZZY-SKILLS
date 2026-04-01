---
name: construction-design-spec
description: |
  生成完整的建筑施工设计说明、建筑设计说明或施工图设计说明，适用于需要根据项目资料抽取信息、裁剪目录并逐章成稿的长流程任务。用户提到“生成整本设计说明”“根据任务书/方案/审图意见整理完整建筑说明”“输出完整建筑工程设计说明”时应使用本技能。若只需润色、翻译、补单章、补小节或回答单条规范问题，则不使用本技能。
compatibility: |
  需要 Bash 运行随附 Python 脚本。知识库检索可使用：
  - RAGFLOW_API_KEY
  - RAGFLOW_BASE_URL
  - RAGFLOW_DATASET_IDS
---

# 建筑施工设计说明文档生成

## 适用边界

- **使用本技能**：生成整本施工设计说明/建筑设计说明/施工图设计说明。
- **不要使用本技能**：润色、翻译、总结、补单章、补小节、回答单条规范问题。
- **单章节请求**：直接在当前上下文处理，不走整套流程。

## 核心规则

1. 先分流，再提取项目信息，再确认目录，再逐章生成，最后整文校验。
2. 地方规范、审查口径、强条适用性没有依据时，不要硬写，标记 `[需人工核验]`。
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
- 可合理推断的内容标记 `[推理补充]`。
- 涉及地方规范、审查口径、强条适用性的结论，没有依据就标记 `[需人工核验]`。
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
python ./scripts/extract_toc.py ./references/public_building_template.md
```

或：

```bash
SCRIPT_ARGS='{"template":"./references/public_building_template.md"}' python ./scripts/extract_toc.py
```

然后输出 `outline_decision.md`，列出：

- 保留章节
- 删除章节及原因
- 需人工核验的地区性或专项章节

裁剪规则：

- 通用章节通常保留。
- 人防、绿建、装配式、海绵城市、幕墙、电梯等按项目条件决定。
- 模板中的城市样例、地方审查要点只能参考；不适用时替换为本项目要求或标记 `[需人工核验]`。
- 模板提示语不得进入最终正文。

用户确认目录后，再进入 Step 3。

## Step 3: 逐章生成

每一章都按 **plan -> retrieve -> draft -> validate** 执行。

### 3.1 提取章节模板

```bash
SCRIPT_ARGS='{"template":"./references/public_building_template.md","chapter":"第1章 设计依据"}' python ./scripts/extract_chapter.py
```

脚本 stdout 即 `chapter_template`。

### 3.2 列 `chapter_plan.json`

```json
{
  "chapter": "第1章 设计依据",
  "applicable": true,
  "coverage_points": ["本章必须覆盖的要点"],
  "missing_info": ["待用户确认或待人工核验的信息"],
  "retrieval_questions": ["为了写好本章，需要向知识库确认的具体问题"]
}
```

只需要说明四件事：这章要不要写、要写什么、缺什么、要问什么。

### 3.3 检索证据

根据 `project_info.json`、`chapter_template`、`chapter_plan.json` 生成几条自然语言问题，再交给 RAGFlow。

示例：

```json
{
  "retrieval_questions": [
    "对于广州体育馆项目，本章通常应列出哪些现行建筑设计依据、专项规范和地方要求？",
    "钢结构加网架屋盖的体育建筑，本章还要补哪些专项规范？",
    "本章哪些地方性要求需要人工核验？"
  ]
}
```

```bash
SCRIPT_ARGS='{"query":"对于广州体育馆项目，本章通常应列出哪些现行建筑设计依据、专项规范和地方要求？","dataset_ids":["your_dataset_id"],"top_k":5,"similarity_threshold":0.1}' python ./scripts/ragflow_query.py
```

检索规则：

- 问题要绑定当前项目和当前章节。
- 先查“该写什么、依据是什么、哪些要核验”。
- 结果不够就继续追问，不要直接开写。
- 优先使用 `SCRIPT_ARGS.dataset_ids`，未传入时回退到 `RAGFLOW_DATASET_IDS`。
- 知识库不可用时，只能输出通用框架和待核验项。

### 3.4 生成正文

结合 `chapter_template`、`project_info.json`、`chapter_plan.json` 和检索结果生成正文：

- 不输出 `XX`、`XXX`
- 可合理补充但并非原文给出的内容标记 `[推理补充]`
- 缺少依据的重要参数标记 `[待补充]`
- 未核实的地方规范或审查口径标记 `[需人工核验]`
- 删除模板中的提示语、示例城市、样例项目名、样例值

### 3.5 章节自检

按 `references/validation_checklist.md` 自检：

- 没有残留 `XX`、`XXX`
- 没有残留无关城市、项目名或样例值
- 没有把模板提示语写进正文
- 章节结论与项目基本信息一致
- 没有在缺乏依据时写出地方性结论

### 3.6 追加到最终文档

单章完成后保留：

- 章节标题
- 章节正文
- 自检结果

自检通过后，立即追加到：

```text
建筑施工设计说明_{项目名称}.md
```

## Step 4: 整文校验与交付

所有章节完成后，再按 `references/validation_checklist.md` 做整文校验：

1. 章节顺序与编号连续
2. 项目名称、地点、面积、高度、层数、结构形式前后一致
3. 同一参数未在不同章节出现冲突
4. 没有残留模板占位符、样例城市、样例项目名
5. 所有 `[需人工核验]` 项已集中列出

交付时说明：

- 最终文档路径
- 关键 `[推理补充]`
- 关键 `[需人工核验]`
- 被裁剪的章节及原因

## 参考文件

- `references/project_info.md`
- `references/validation_checklist.md`
- `references/public_building_template.md`

优先执行：

- `scripts/extract_toc.py`
- `scripts/extract_chapter.py`
- `scripts/ragflow_query.py`

## 常见错误

| 错误 | 正确做法 |
|------|----------|
| 单章节请求却启动整套流程 | 单章需求直接处理 |
| 还没确认关键信息就开始写正文 | 先补齐项目关键字段 |
| 没有知识库还直接写地方规范结论 | 只输出通用框架，并标记 `[需人工核验]` |
| 输出残留样例城市、样例项目名、模板提示语 | 每章生成后立即自检清洗 |
| 一次性并行生成多章 | 严格按章节顺序生成 |
