#!/usr/bin/env python3
"""
RAGFlow 知识库查询脚本

通过 RAGFlow REST API 查询知识库，返回检索结果。

环境变量（由 harness 注入）:
    RAGFLOW_API_KEY      - API 密钥
    RAGFLOW_BASE_URL     - RAGFlow 服务地址（默认: https://rag.aizzyun.com）
    RAGFLOW_DATASET_IDS  - 知识库 ID，多个用逗号分隔

SCRIPT_ARGS (JSON):
    {
        "query": "查询文本",
        "dataset_ids": ["dataset_id_1", "dataset_id_2"],
        "top_k": 5,
        "similarity_threshold": 0.1
    }
"""

import json
import os
import sys
from typing import Any


def _load_env_if_missing():
    """若环境变量未设置，尝试从 .env 文件加载（支持 shell 和 JSON 格式）。"""
    required = ["RAGFLOW_API_KEY", "RAGFLOW_BASE_URL", "RAGFLOW_DATASET_IDS"]
    if all(os.environ.get(k) for k in required):
        return
    # .env 位于 scripts 目录（与脚本同目录）
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "RAGFLOW_DATASET_IDS":
                    # 可能是 JSON 数组或逗号分隔
                    try:
                        parsed = json.loads(val)
                        if isinstance(parsed, list):
                            val = ",".join(parsed)
                    except Exception:
                        pass
                if key.startswith("RAGFLOW_") and key not in os.environ:
                    os.environ[key] = val


def get_env(key: str, default: str = "") -> str:
    _load_env_if_missing()
    return os.environ.get(key, default)


def get_dataset_ids(parsed: dict[str, Any]) -> list[str]:
    dataset_ids = parsed.get("dataset_ids")
    if dataset_ids:
        return [str(item).strip() for item in dataset_ids if str(item).strip()]

    env_ids = get_env("RAGFLOW_DATASET_IDS", "")
    if env_ids:
        # 优先尝试 JSON 数组解析
        try:
            parsed_ids = json.loads(env_ids)
            if isinstance(parsed_ids, list):
                return [str(item).strip() for item in parsed_ids if str(item).strip()]
        except Exception:
            pass
        # 降级为逗号分隔
        return [item.strip() for item in env_ids.split(",") if item.strip()]

    return []


def ragflow_query(
    query: str,
    dataset_ids: list[str],
    top_k: int = 5,
    similarity_threshold: float = 0.1,
) -> dict[str, Any]:
    """调用 RAGFlow API 查询知识库。"""
    api_key = get_env("RAGFLOW_API_KEY")
    base_url = get_env("RAGFLOW_BASE_URL", "https://rag.aizzyun.com").rstrip("/")

    if not api_key:
        return {
            "success": False,
            "error": "RAGFLOW_API_KEY 环境变量未设置",
            "fallback": True,
        }

    if not dataset_ids:
        return {
            "success": False,
            "error": "未提供 dataset_ids；请通过 SCRIPT_ARGS.dataset_ids 或 RAGFLOW_DATASET_IDS 配置知识库 ID",
            "fallback": True,
        }

    datasets_url = f"{base_url}/api/v1/datasets"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 分页获取所有知识库，查找目标 ID
    try:
        import urllib.request

        valid_ids = []
        page = 1
        while True:
            req = urllib.request.Request(
                f"{datasets_url}?page={page}", headers=headers, method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                datasets_data = json.loads(resp.read().decode("utf-8"))

            for ds in datasets_data.get("data", []):
                if ds.get("id") in dataset_ids:
                    valid_ids.append(ds.get("id"))

            # 判断是否还有下一页：返回数量 < 30 则已到最后一页
            if len(datasets_data.get("data", [])) < 30:
                break
            page += 1
    except Exception as e:
        return {
            "success": False,
            "error": f"连接 RAGFlow 失败: {str(e)}",
            "fallback": True,
        }

    if not valid_ids:
        return {
            "success": False,
            "error": f"未找到匹配的知识库: {dataset_ids}",
            "fallback": True,
        }

    search_url = f"{base_url}/api/v1/retrieval"
    payload = {
        "question": query,
        "dataset_ids": valid_ids,
        "top_k": top_k,
        "similarity_threshold": similarity_threshold,
    }

    try:
        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            search_url,
            data=data,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        if result.get("code") != 0:
            return {
                "success": False,
                "error": result.get("message", "API 返回错误"),
                "fallback": True,
            }

        chunks = []
        data_obj = result.get("data", {})
        if data_obj:
            for item in data_obj.get("chunks", []):
                content = item.get("content", "")
                if content:
                    chunks.append(content)

        if not chunks:
            return {
                "success": False,
                "error": "检索结果为空，知识库中无相关内容",
                "fallback": True,
                "query": query,
                "results": [],
                "count": 0,
            }

        return {
            "success": True,
            "query": query,
            "results": chunks,
            "count": len(chunks),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"检索失败: {str(e)}",
            "fallback": True,
        }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parsed: dict[str, Any] = {}
    script_args = os.environ.get("SCRIPT_ARGS", "")
    if script_args:
        try:
            parsed = json.loads(script_args)
        except Exception:
            pass

    if len(sys.argv) > 1:
        try:
            parsed = json.loads(sys.argv[1])
        except Exception:
            pass

    query = parsed.get("query", "")
    dataset_ids = get_dataset_ids(parsed)
    top_k = parsed.get("top_k", 5)
    similarity_threshold = parsed.get("similarity_threshold", 0.1)

    if not query:
        print("Error: query is required")
        sys.exit(1)

    result = ragflow_query(query, dataset_ids, top_k, similarity_threshold)

    if result["success"]:
        print(f"=== RAGFlow 检索结果 ({result['count']} 条) ===\n")
        for i, chunk in enumerate(result["results"], 1):
            print(f"--- 结果 {i} ---")
            print(chunk[:2000] if len(chunk) > 2000 else chunk)
            print()
        return

    if result.get("fallback"):
        print(f"[INFO] RAGFlow 不可用: {result['error']}")
        print("[INFO] RAGFlow 检索是强制前置条件，无法生成章节。请检查知识库服务状态后重试。")
        return

    print(f"Error: {result.get('error', 'Unknown error')}")
    sys.exit(1)


if __name__ == "__main__":
    main()
