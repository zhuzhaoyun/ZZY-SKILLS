---
name: weknora
description: Use when the user mentions knowledge base, wiki, 知识库, 查知识库, 搜知识库, 维基问答, 知识图谱, or says "帮我查一下知识库", "知识库里有没有", "wiki 里找找", "导入文档". Also for uploading files, editing wiki pages, or any WeKnora operation.
---

# WeKnora

通过 Chat API 检索知识库，通过 REST API 管理知识库（导入、编辑、维护）。

## Setup

```bash
export WEKNORA_BASE_URL="https://your-server.com/api/v1"
export WEKNORA_API_KEY="sk-your-api-key"
```

调用前检查凭证，缺失则提示用户配置。

> **Windows 编码注意**（Git Bash / MSYS2 下必须遵守）：
> 1. **禁止 curl `-d` 传中文**：MSYS2 会把命令行参数中的非 ASCII 字符从 UTF-8 转成 GBK，导致服务端收到乱码。含中文的 JSON 必须用 Python 生成后通过管道 `--data-binary @-` 传给 curl。
> 2. **Python stdin 默认 GBK**：`curl | python -c` 管道中，Python `sys.stdin` 默认用 cp936，会破坏 UTF-8 中文。所有 `python -c` 调用前必须加 `PYTHONIOENCODING=utf-8`。

```bash
# GET 请求（无中文 body，可用 curl）
wk_get() {
  local endpoint="$1"
  curl -s -X GET "$WEKNORA_BASE_URL/$endpoint" \
    -H "X-API-Key: $WEKNORA_API_KEY" \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: $(uuidgen 2>/dev/null || date +%s)"
}

# POST/PUT 含中文 body（用 Python 生成 UTF-8 JSON，管道传给 curl）
wk_post() {
  local method="$1" endpoint="$2" json_body="$3"
  printf '%s' "$json_body" | curl -s -X "$method" "$WEKNORA_BASE_URL/$endpoint" \
    -H "X-API-Key: $WEKNORA_API_KEY" \
    -H "Content-Type: application/json; charset=utf-8" \
    -H "X-Request-ID: $(uuidgen 2>/dev/null || date +%s)" \
    --data-binary @-
}
```

文件上传用 `curl -F` (multipart/form-data)。

> 路由区别：KB 管理 `/knowledge-bases/` (plural)，Wiki 管理 `/knowledgebase/:kb_id/wiki/` (singular)。

---

## Chat API (Primary)

所有自然语言提问走 Chat API，由服务端 Agent 完成完整检索和推理。

### Agents

| Agent ID | 模式 | 场景 |
|---|---|---|
| `builtin-wiki-researcher` | 维基问答 (ReAct) | **默认**，wiki 已启用 |
| `builtin-quick-answer` | 快速问答 (RAG) | 简单事实，低延迟 |
| `builtin-smart-reasoning` | 智能推理 (ReAct) | 多步推理，无 wiki |
| `builtin-deep-researcher` | 深度研究 | 复杂调研 |
| `builtin-data-analyst` | 数据分析 | CSV/Excel SQL |
| `builtin-knowledge-graph-expert` | 知识图谱 | 图谱查询 |
| `builtin-document-assistant` | 文档助手 | 单文档深度问答 |

### Workflow

```
1. GET /knowledge-bases                    → kb_id, 读取 capabilities 判断 wiki/faq/graph 是否启用
2. POST /sessions  {"title":"主题"}         → session_id
3. POST /agent-chat/<session_id>           → SSE stream
   {"query":"问题", "knowledge_base_ids":["<kb_id>"],
    "agent_id":"根据 capabilities 选择的 agent", "agent_enabled":true}
```

**KB 能力字段路径**（从 list 或 detail 响应中读取）：

| 能力 | 字段路径 | 值 |
|---|---|---|
| Wiki 已启用 | `capabilities.wiki` | `true`/`false` |
| 知识图谱已启用 | `capabilities.graph` | `true`/`false` |
| FAQ 已启用 | `capabilities.faq` | `true`/`false` |

**Agent 选择逻辑**（按优先级）：

1. `capabilities.wiki == true` → `builtin-wiki-researcher`
2. `capabilities.graph == true` 且用户问图谱 → `builtin-knowledge-graph-expert`
3. 以上都未启用 → `builtin-smart-reasoning`
4. 用户指定了具体 agent → 使用用户指定的

### SSE Response

`event: message`，语义由 `data.response_type` 决定：

| response_type | 含义 |
|---|---|
| `thought` | Agent 思考 |
| `action` | 调工具 (`tool_name`, `tool_input`) |
| `observation` | 工具返回 |
| `answer` | 流式文本片段 (`content`, `done:false`) |
| `complete` | 流结束 (`total_duration_ms`) |
| `error` | 出错 |

提取完整答案（Windows 下必须设 `PYTHONIOENCODING=utf-8`，否则 stdin 按 GBK 解码导致中文乱码）：

```bash
curl -sN ... | PYTHONIOENCODING=utf-8 python -c "
import sys, json
parts = []
for line in sys.stdin:
    if not line.startswith('data:'): continue
    try: d = json.loads(line[5:].strip())
    except: continue
    if d.get('response_type') == 'answer' and d.get('content'):
        parts.append(d['content'])
    elif d.get('response_type') == 'complete': break
print(''.join(parts))"
```

### Example

```bash
# 1. 获取 kb_id 和 wiki 状态（GET 请求无中文 body，直接 curl）
eval $(wk_get "knowledge-bases" | PYTHONIOENCODING=utf-8 python -c "
import sys,json
kbs = json.load(sys.stdin)['data']
kb = kbs[0]
wiki = kb.get('capabilities',{}).get('wiki', False)
print(f'KB_ID={kb[\"id\"]} WIKI_ENABLED={str(wiki).lower()}')")

# 2. 根据 wiki 状态选择 agent
AGENT="builtin-smart-reasoning"
[ "$WIKI_ENABLED" = "true" ] && AGENT="builtin-wiki-researcher"

# 3. 创建会话（中文 title 通过 printf 管道传，不用 curl -d）
SID=$(printf '{"title":"查询"}' | curl -s -X POST "$WEKNORA_BASE_URL/sessions" \
  -H "X-API-Key: $WEKNORA_API_KEY" -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @- | PYTHONIOENCODING=utf-8 python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

# 4. 查询（JSON body 用 printf 管道传给 curl，禁止 -d 传中文）
printf '{"query":"问题","knowledge_base_ids":["%s"],"agent_id":"%s","agent_enabled":true}' "$KB_ID" "$AGENT" \
  | curl -sN -X POST "$WEKNORA_BASE_URL/agent-chat/$SID" \
    -H "X-API-Key: $WEKNORA_API_KEY" -H "Content-Type: application/json; charset=utf-8" \
    -H "Accept: text/event-stream" --max-time 120 --data-binary @- \
  | PYTHONIOENCODING=utf-8 python -c "
import sys,json; parts=[]
for l in sys.stdin:
  if not l.startswith('data:'): continue
  try: d=json.loads(l[5:].strip())
  except: continue
  if d.get('response_type')=='answer' and d.get('content'): parts.append(d['content'])
  elif d.get('response_type')=='complete': break
print(''.join(parts))"
```

---

## File Back: 归档有价值的分析

跨页面综合分析、对比、深层洞察写回 wiki 复利。简单问答不归档。

```bash
# synthesis 页（中文内容通过 wk_post 管道传，不用 curl -d）
wk_post POST "knowledgebase/<kb_id>/wiki/pages" '{
  "slug":"synthesis/<slug>","title":"标题","page_type":"synthesis",
  "content":"# 标题\n\n综合 [[entity/A]] 和 [[concept/B]]..."}'

# comparison 页
wk_post POST "knowledgebase/<kb_id>/wiki/pages" '{
  "slug":"comparison/<slug>","title":"A vs B","page_type":"comparison",
  "content":"# A vs B\n\n| 维度 | [[entity/A]] | [[entity/B]] |\n|------|---|---|\n| ... |"}'
```

Wiki 页面标记：`[[slug|title]]` 交叉链接，`[c001]` 来源引用。

---

## Management APIs (REST)

### KB 管理

| Endpoint | 用途 |
|---|---|
| `GET /knowledge-bases` | 列出 KB |
| `GET /knowledge-bases/:id` | KB 详情 |
| `POST /knowledge-bases/:id/knowledge/file` | 上传文件 (form-data: `file`, `enable_multimodel`) |
| `POST /knowledge-bases/:id/knowledge/url` | 导入网页 (`url`, `enable_multimodel`) |
| `POST /knowledge-bases/:id/knowledge/manual` | 写入 Markdown (`title`, `content`) |
| `GET /knowledge/:id` | 查询解析状态 (`parse_status`: pending/processing/completed/failed) |
| `PUT /knowledge/manual/:id` | 编辑 Markdown |
| `DELETE /knowledge/:id` | 删除 |

### Wiki 管理

| Endpoint | 用途 |
|---|---|
| `GET /knowledgebase/:kb_id/wiki/stats` | 概览 |
| `GET /knowledgebase/:kb_id/wiki/lint` | 健康检查 |
| `POST /knowledgebase/:kb_id/wiki/auto-fix` | 自动修复 |
| `POST /knowledgebase/:kb_id/wiki/rebuild-links` | 重建双向链接 |
| `GET /knowledgebase/:kb_id/wiki/log?per_page=10` | 操作日志 |
| `GET /knowledgebase/:kb_id/wiki/graph` | 图谱 (`mode`: overview/ego, `center`, `depth`) |
| `GET /knowledgebase/:kb_id/wiki/pages` | 列出页面 |
| `GET /knowledgebase/:kb_id/wiki/pages/*slug` | 读取页面 |
| `PUT /knowledgebase/:kb_id/wiki/pages/*slug` | 更新页面 |
| `DELETE /knowledgebase/:kb_id/wiki/pages/*slug` | 删除页面 |

Lint 后主动建议：缺失页面、过时信息、值得深入的方向、填补空白的来源文档。

## Error Handling

| Code | Action |
|---|---|
| 401 | 检查 `WEKNORA_API_KEY` |
| 404 | 检查资源 ID/slug |
| 413 | 减小文件大小或拆分 |
| 500 | 短暂延迟后重试 |
