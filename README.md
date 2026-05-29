# ZZY-SKILLS

我的 Claude Code Skill 合集。每个 Skill 都是针对特定工作场景的 Agent 技能包，拿来即用。

## 为什么开源这些 Skill

在 AI Agent 落地实践中，我发现一个规律：**真正决定 Agent 能力上限的，不是模型本身，而是你围绕它建起来的 Harness（约束环境）。** Skill 是 Harness 的核心组件之一——它把领域经验、工作流程、工具调用封装成 Agent 可以直接复用的能力单元。

这些 Skill 来自真实的业务场景，不是玩具 demo。每个都经过反复打磨，解决了具体的工程问题。

## Skill 列表

### weknora-for-wiki — 知识库检索与维护

通过 WeKnora Chat API 检索知识库，通过 REST API 管理知识库（导入、编辑、wiki 页面维护、健康检查）。

**核心理念：** 知识库应该由 Agent 自己维护，而不是人来手动操作。支持 File Back 机制——有价值的综合分析自动写回 wiki，实现知识复利。

**触发词：** `知识库`、`查知识库`、`wiki 里找找`、`导入文档`、`知识库里有没有`

**支持的能力：**
- 自然语言查询（自动选择 Wiki 问答/快速问答/智能推理等 Agent 模式）
- 文件上传、URL 导入、Markdown 写入
- Wiki 页面 CRUD、交叉链接、健康检查（Lint）
- SSE 流式响应处理

→ 详见 [weknora-for-wiki/SKILL.md](weknora-for-wiki/SKILL.md)

### construction-design-spec — 建筑施工设计说明生成

长流水线 Skill，生成完整的建筑施工设计说明文档。

**工作流程：** 环境检查 → 项目信息提取 → 目录确认 → 逐章生成（Sub-Agent + RAGFlow 强制检索）→ 全文验证

**关键设计：**
- 每章必须经过 RAGFlow 知识库检索，不可用则终止（防止幻觉）
- 脚本驱动的模板提取，确保格式一致
- 严格的反幻觉规则：无占位符、无示例数据、无降级生成

→ 详见 [construction-design-spec/SKILL.md](construction-design-spec/SKILL.md)

### construction-org-design-spec — 公路工程施工组织设计生成

与建筑施工设计说明类似的流水线，专注于公路/桥梁/隧道工程的施工组织设计文档。

**领域特化：** 覆盖道路等级、设计速度、路面结构、桥梁/隧道参数、地质水文、交通管理等公路工程专属信息模型。

→ 详见 [construction-org-design-doc/SKILL.md](construction-org-design-doc/SKILL.md)

### meeting-minutes — 会议纪要整理

将杂乱的会议输入（语音转文字、手写笔记、草稿）转化为结构化 Markdown 会议纪要。

**亮点功能：**
- **隐式待办提取** —— 识别"我回头看看"、"下周约一下"等口语化表达，自动转化为可追踪的 TODO
- 自动检测会议类型（决策会/同步会/头脑风暴）并应用对应模板
- 按主题分组（不是按时间顺序复述）
- 不确定内容标记 🌀

**触发词：** `整理纪要`、`整理会议记录`、`写会议纪要`、`总结会议内容`、`提取待办`

→ 详见 [meeting-minutes/SKILL.md](meeting-minutes/SKILL.md)

### ue-review — 前端交互体验（UE/UX）评估

从 8 个维度评估前端交互质量：交互反馈、状态可见性、任务流效率、弹窗/覆盖层、布局/空间、一致性、错误预防、可发现性。

**两种模式：**
- **Review**：审查现有页面 → 结构化报告
- **Guidance**：设计阶段的交互建议

**输出格式：** 问题列表（位置、影响、修复建议、检查项引用）+ 严重度标记（🔴 Critical / 🟡 Major / 🟢 Minor）+ 覆盖率报告

**触发词：** `UE`、`UX`、`交互体验`、`交互审查`、`一致性`、`错误预防`

→ 详见 [ue-review/SKILL.md](ue-review/SKILL.md)

### daily-guidelines — 日常任务行为准则

基于 Andrej Karpathy 对 LLM 常见陷阱的观察，提炼出 4 条行为准则，减少 Agent 在日常办公任务中的典型错误。

**四条准则：**

1. **先想再做** —— 显式声明假设，存在多种理解时呈现选项而非默默选一个，不确定就停下来问
2. **极简优先** —— 不加没要求的工具、不做一次性任务的复杂工作流、不为不可能发生的场景做兜底
3. **聚焦执行** —— 只改必须改的，不"顺手优化"无关内容，匹配已有风格，每行改动都能追溯到用户的请求
4. **目标驱动** —— 把任务转化为可验证目标（"写邮件" → "起草邮件 + 确认语气匹配收件人 + 核实所有要点已覆盖"），定义成功标准后循环执行直到验证通过

**适用场景：** 任何 Agent 任务——写文档、编辑内容、整理资料、管理待办。这不是一个特定领域的 Skill，而是一套通用的"防翻车指南"。

→ 详见 [daily-guidelines/SKILL.md](daily-guidelines/SKILL.md)

## 使用方式

每个 Skill 是独立的目录，包含 `SKILL.md` 文件。在 Claude Code 中使用时，将 Skill 目录放入项目的 `.claude/skills/` 下即可自动加载。

```bash
# 示例：安装 weknora-for-wiki
cp -r weknora-for-wiki/ your-project/.claude/skills/
```

部分 Skill 需要环境变量配置（如 API Key），详见各 Skill 的 SKILL.md。

## 关于我

独立开发者，专注 AI Agent 工程化落地。如果你也在探索如何让 Agent 真正融入业务流程，欢迎交流。

## License

MIT
