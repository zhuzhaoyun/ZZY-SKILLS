---
name: weknora-wiki
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

```bash
wk_api() {
  local method="$1" endpoint="$2" body="$3"
  curl -s -X "$method" "$WEKNORA_BASE_URL/$endpoint" \
    -H "X-API-Key: $WEKNORA_API_KEY" \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: $(uuidgen 2>/dev/null || date +%s)" \
    ${body:+-d "$body"}
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

提取完整答案：

```python
import sys, json
parts = []
for line in sys.stdin:
    if not line.startswith("data:"): continue
    try: d = json.loads(line[5:].strip())
    except: continue
    if d.get("response_type") == "answer" and d.get("content"):
        parts.append(d["content"])
    elif d.get("response_type") == "complete": break
print("".join(parts))
```

### Example

```bash
# 1. 获取 kb_id 和 wiki 状态
eval $(wk_api GET "knowledge-bases" | python -c "
import sys,json
kbs = json.load(sys.stdin)['data']
kb = kbs[0]
wiki = kb.get('capabilities',{}).get('wiki', False)
print(f'KB_ID={kb[\"id\"]} WIKI_ENABLED={str(wiki).lower()}')")

# 2. 根据 wiki 状态选择 agent
AGENT="builtin-smart-reasoning"
[ "$WIKI_ENABLED" = "true" ] && AGENT="builtin-wiki-researcher"

# 3. 创建会话并查询
SID=$(curl -s -X POST "$WEKNORA_BASE_URL/sessions" \
  -H "X-API-Key: $WEKNORA_API_KEY" -H "Content-Type: application/json" \
  -d '{"title":"query"}' | python -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

curl -sN -X POST "$WEKNORA_BASE_URL/agent-chat/$SID" \
  -H "X-API-Key: $WEKNORA_API_KEY" -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" --max-time 120 \
  -d '{"query":"问题","knowledge_base_ids":["'$KB_ID'"],"agent_id":"'"$AGENT"'","agent_enabled":true}' \
  | python -c "
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
# synthesis 页
wk_api POST "knowledgebase/<kb_id>/wiki/pages" '{
  "slug":"synthesis/<slug>","title":"标题","page_type":"synthesis",
  "content":"# 标题\n\n综合 [[entity/A]] 和 [[concept/B]]..."}'

# comparison 页
wk_api POST "knowledgebase/<kb_id>/wiki/pages" '{
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
