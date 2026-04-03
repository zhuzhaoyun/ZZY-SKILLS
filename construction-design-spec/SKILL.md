---
name: construction-design-spec
description: |
  生成完整的建筑施工设计说明、建筑设计说明或施工图设计说明，适用于需要根据项目资料抽取信息、裁剪目录并逐章成稿的长流程任务。用户提到"生成整本设计说明""根据任务书/方案/审图意见整理完整建筑说明""输出完整建筑工程设计说明"时应使用本技能。若只需润色、翻译、补单章、补小节或回答单条规范问题，则不使用本技能。
compatibility: |
  需要 Bash 运行随附 Python 脚本
---

# 建筑施工设计说明文档生成

## 适用边界

- **使用本技能**：生成整本施工设计说明/建筑设计说明/施工图设计说明。
- **不要使用本技能**：润色、翻译、总结、补单章、补小节、回答单条规范问题。
- **单章节请求**：直接在当前上下文处理，不走整套流程。

## 核心规则

1. **所有步骤必须通过脚本执行，禁止手动读取模板后直接生成内容。**
2. 模板中的占位符（如 `xxx`）应结合项目信息主动推理填充，**禁止保留任何占位符**。
3. 目录和章节优先用脚本提取，不手工抄模板。
4. 各章必须串行生成；上一章没过校验，不要开始下一章。
5. **RAGFlow 检索失败 = 立即中止生成，向用户报告。禁止在 RAG 不可用时降级生成。**

## 禁止行为清单

| 禁止行为 | 正确做法 |
|----------|----------|
| 手动读取模板文件然后直接生成内容 | 运行 `extract_toc.py` / `extract_chapter.py` 提取 |
| 凭记忆或推理生成内容而不检索 RAGFlow | 每章必须调用 `ragflow_query.py` 检索 |
| RAGFlow 不可用时降级生成通用框架 | 中止生成，输出错误报告 |
| 保留 `XX`、`XXX`、`xxx` 等占位符 | 用项目信息推理填充 |
| 在正文中保留模板提示语（如"如不涉及可删除"） | 生成后自检清洗 |
| 保留样例城市名、样例项目名、样例数值 | 替换为项目真实值 |
| 并行生成多章而不经校验 | 逐章串行，上一章校验通过才下一章 |

## 推荐中间产物

- `project_info.json`
- `outline_decision.md`
- `chapter_plan_{sanitized_name}.json`（每章一个）
- `建筑施工设计说明_{项目名称}.md`

## 参考文件

- `references/project_info.md`
- `references/validation_checklist.md`
- `assets/public_building_template.md`

## 脚本清单（按执行顺序，必须运行）

- `scripts/extract_toc.py` — Step 2 提取模板目录
- `scripts/extract_chapter.py` — Step 3 提取单章模板内容
- `scripts/ragflow_query.py` — Step 3 检索知识库（强制前置条件）

---

## 工作流

```text
Step 0: 环境检查
Step 1: 项目信息提取
Step 2: 大纲确认与裁剪
Step 3: 逐章生成（子代理执行）
Step 4: 整文校验与交付
```

## Step 0: 环境检查

**必须先验证执行环境可用，再开始后续步骤。**

1. 确认模板文件存在：`ls ./assets/public_building_template.md`
2. 确认脚本可执行：`python ./scripts/extract_toc.py --help` 或检查脚本语法
3. 确认 RAGFlow 可用：运行一条测试查询
   ```bash
   SCRIPT_ARGS='{"query":"测试","top_k":1,"similarity_threshold":0.3}' python ./scripts/ragflow_query.py
   ```
   - 成功：进入 Step 1
   - 失败（exit code 1）：检查 `scripts/.env` 文件是否存在，`RAGFLOW_API_KEY`、`RAGFLOW_BASE_URL`、`RAGFLOW_DATASET_IDS` 是否配置正确

## Step 1: 项目信息提取

读取 `references/project_info.md` 中的提示词模板，结合项目概要、任务书、方案文本、审图意见、地方要求等资料，生成 `project_info.json`。

**`project_info.json` 格式示例**（完整 schema 见 `references/project_info.md`）：

```json
{
  "项目名称": "xxx",
  "建设地点": "xxx",
  "建筑面积": "xxx m²",
  "层数": "地上x层/地下x层",
  "建筑高度": "xxx m",
  "结构形式": "框架结构",
  "气候分区": "严寒/寒冷/夏热冬冷/夏热冬暖",
  "是否人防": "是/否",
  "是否绿建": "是/否",
  "是否装配式": "是/否"
}
```

提取规则：

- 原文明确给出的参数直接提取。
- 原文未提及的常见参数，按一般项目特征推理补充（如气候分区按城市推断、耐火等级按建筑类型推断），推理结果标注 `[推理补充]`。
- 涉及地方规范、审查口径、强条适用性的内容，如有依据则写，无依据则参考类似项目写法或合理推断，推理结果标注 `[推理补充]`，不要留任何占位符标记。
- 所有数值保留单位。
- **信息不足时**：不阻塞流程，先按一般项目特征推理补充所有字段，再将 `project_info.json` 展示给用户确认。用户可纠正后继续。

进入 Step 2 前至少确认：

- 项目名称
- 建设地点
- 建筑类型 / 使用功能
- 建筑面积、层数、高度
- 结构形式
- 是否涉及地下室、人防、幕墙、电梯、装配式、绿建等专项

**禁止未确认项目信息就进入 Step 2。**

## Step 2: 大纲确认与裁剪

**必须运行脚本提取模板目录，禁止手动读取模板后手工抄录目录。**

```bash
python ./scripts/extract_toc.py ./assets/public_building_template.md
```

或：

```bash
SCRIPT_ARGS='{"template":"./assets/public_building_template.md"}' python ./scripts/extract_toc.py
```

然后输出 `outline_decision.md`，列出：

- 保留章节
- 裁剪章节及理由

**用户确认目录示例**：
> 请确认以下大纲是否适用本项目：
> - 1.工程概况、2.设计依据、...（完整列表）
>
> 确认后我将开始逐章生成。

**用户确认目录后，再进入 Step 3。** 
*禁止未确认目录就进入 Step 3。**


## Step 3: 逐章生成

**每章必须独立执行完整流程：提取模板 → RAGFlow 检索 → 生成草稿 → 校验 → 追加到最终文档。**

### 3.1 子代理执行策略

从 `outline_decision.md` 的"保留章节"列表中，依次取出每一章，**对每一章分别使用 Agent 工具 spawn 一个子代理**。

**Spawn 参数**：
- **chapter_name**：outline 中保留章节的完整名称（如 `21.节能设计`）
- **project_info_path**：`project_info.json` 的绝对路径
- **output_dir**：子代理的工作目录，默认为 `./output/{项目名称}/`，subagent 会在其下创建 `chapters/{sanitized_name}/` 目录
- **final_doc_path**：最终文档的绝对路径，默认为 `./output/{项目名称}/建筑施工设计说明_{项目名称}.md`

**Spawn 方法**（使用 Agent 工具）：

1. 先读取 `agents/chapter-generator.md` 获取完整子代理指令
2. 对每一章，调用 Agent 工具，参数如下：
   - `subagent_type`: `general-purpose`
   - `prompt`: （`agents/chapter-generator.md` 的内容 + 以下参数注入）
   - `description`: `生成第{X}章: {chapter_name}`
   - 如果环境支持 `run_in_background`，可设为 `true` 并行等待
3. 等待子代理完成后检查输出，再继续下一章

```
for chapter in ["1.工程概况", "2.设计依据", "21.节能设计", ...]:
    1. Read agents/chapter-generator.md → 获取子代理指令
    2. Agent tool:
       subagent_type = "general-purpose"
       prompt = chapter-generator.md内容 + 以下参数:
         chapter_name = "{chapter}"
         project_info_path = "{path}"
         output_dir = "{path}"
         final_doc_path = "{path}"
    3. 等待完成，检查输出文件是否齐全
    4. 下一章
```

**子代理所需最小工具集**：Bash、Read、Write、Glob、Grep。spawn 前确认子代理具备 Bash 工具权限。

**前置权限检查**：在 spawn 第一个子代理前，先用一个轻量测试确认 Agent 工具可用且子代理具备 Bash 权限：
```
调用 Agent 工具，subagent_type="general-purpose", prompt="运行 echo test 并返回结果"
```
- 测试成功：正常 spawn 章节生成子代理
- 测试失败：说明当前环境不支持 Agent 工具或子代理无 Bash 权限，**必须改为在主会话中逐章串行执行**：
  1. 读取 `agents/chapter-generator.md` 获取每章的执行流程
  2. 对每一章依次执行：extract_chapter.py → ragflow_query.py → 生成草稿 → 校验 → 追加到最终文档
  3. **每章必须创建独立子目录**，保存 `template_chapter.txt`、`ragflow_output.txt`（或 `retrieval.json`）、`chapter_draft.md`、`chapter_result.md`
  4. 每章必须调用 `ragflow_query.py` 进行专项检索，不得所有章节共用同一 query

### 3.2 RAGFlow 检索强制要求

**RAGFlow 检索是强制前置条件。检索失败（exit code 1、网络错误、API 不可用、无响应）= 立即中止生成，向用户报告企业知识库不可用。不得伪造检索结果，不得在 RAG 不可用时降级生成通用框架。**

每章的检索 query 必须针对本章内容专项生成，不得所有章节使用同一个 query。

### 3.3 章节校验

每章生成后必须按 `references/validation_checklist.md` 进行自检，校验通过才追加到最终文档。校验不通过时修复后重新校验。

## Step 4: 整文校验与交付

所有章节完成后，按 `references/validation_checklist.md` 做整文校验：

1. 章节顺序与编号连续
2. 项目名称、地点、面积、高度、层数、结构形式前后一致
3. 同一参数未在不同章节出现冲突
4. 没有残留模板占位符（`XX`、`XXX`、`xxx`）
5. 没有残留样例城市、样例项目名、模板提示语
6. 所有 `[需人工核验]` 项已集中列出

**校验方式**：逐条对照 `references/validation_checklist.md` 清单，使用 Grep 搜索残留占位符和模板关键字（如"样例"、"如不涉及"、"可删除此条"）。

校验不通过时，修复问题后重新执行整文校验，直到全部通过。

交付时说明：

- 最终文档路径
- 校验结果（通过/未通过及修复记录）
- 需要人工核验的事项列表（如有）
