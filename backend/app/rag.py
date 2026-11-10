"""RAG 对话引擎：检索增强生成（Retrieval-Augmented Generation）。

管线：简历文本切块 → 嵌入向量化 → 余弦相似度检索 Top-K 相关片段
      → 拼接提示词 → LLM 流式生成回答。

嵌入双模式：
- 配置了 LLM_API_KEY：调用 OpenAI 兼容 /embeddings 接口（text-embedding-3-small）
- 未配置：本地哈希 n-gram 嵌入兜底（零依赖、确定性，效果弱于真嵌入但可离线演示）

回答双模式：
- LLM 模式：SSE 流式转发大模型输出
- 规则模式：基于检索片段 + 分析结果组装回答，逐句流式输出（零配置可演示）
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator

import httpx

from .config import settings

EMBED_DIM = 512
CHUNK_SIZE = 180      # 每块约 180 字
CHUNK_OVERLAP = 40    # 块间重叠，保证语义连续
TOP_K = 4


# ---------- 文本切块 ----------

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按固定窗口 + 重叠把简历文本切成检索块。"""
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        piece = clean[start : start + size]
        if piece.strip():
            chunks.append(piece)
        start += size - overlap
    return chunks


# ---------- 嵌入 ----------

def _local_embed(text: str) -> list[float]:
    """本地兜底嵌入：字符 2-gram 哈希到 512 维后 L2 归一化。零依赖、确定性。"""
    vec = [0.0] * EMBED_DIM
    grams = [text[i : i + 2] for i in range(len(text) - 1)] or [text]
    for g in grams:
        idx = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % EMBED_DIM
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


async def _llm_embed(texts: list[str]) -> list[list[float]] | None:
    """调用 OpenAI 兼容嵌入接口；失败（无 key / 网络问题）返回 None 走兜底。"""
    if not settings.LLM_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                json={"model": getattr(settings, "LLM_EMBED_MODEL", "text-embedding-3-small"), "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]
    except Exception:
        return None


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


async def retrieve(resume_text: str, question: str, top_k: int = TOP_K) -> tuple[list[str], bool]:
    """返回 (Top-K 相关块, 是否使用 LLM 嵌入)。"""
    chunks = chunk_text(resume_text)
    if not chunks:
        return [], False

    llm_vecs = await _llm_embed([question, *chunks])
    if llm_vecs:
        q_vec, chunk_vecs = llm_vecs[0], llm_vecs[1:]
        used_llm = True
    else:
        q_vec = _local_embed(question)
        chunk_vecs = [_local_embed(c) for c in chunks]
        used_llm = False

    scored = sorted(
        zip(chunks, chunk_vecs),
        key=lambda cv: _cosine(q_vec, cv[1]),
        reverse=True,
    )
    return [c for c, _ in scored[:top_k]], used_llm


# ---------- 提示词与回答 ----------

def build_prompt(question: str, chunks: list[str], context: dict) -> list[dict]:
    """组装 OpenAI 兼容的 messages。context 含最新分析结果。"""
    evidence = "\n---\n".join(chunks)
    dims = context.get("dimensions", {})
    dim_lines = "\n".join(f"- {d['label']}: {d['score']}/{d['max']}" for d in dims.values()) or "无"
    missing = "、".join(context.get("missing_keywords", [])) or "无"
    system = (
        "你是简历诊断助手。仅根据提供的简历片段与诊断数据回答用户关于简历修改的问题，"
        "给出具体、可执行的修改建议（最好提供改写示例）。回答使用中文，控制在 300 字以内。"
        "如果片段中没有相关信息，明确说明，不要编造。"
    )
    user = (
        f"【简历相关片段】\n{evidence}\n\n"
        f"【诊断数据】总分 {context.get('score', '-')}/100；维度得分：\n{dim_lines}\n缺失关键词：{missing}\n\n"
        f"【用户问题】{question}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def _stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    """SSE 流式调用 LLM，逐 token 产出。"""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            json={
                "model": settings.LLM_MODEL,
                "messages": messages,
                "stream": True,
                "temperature": 0.4,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta


def _rule_answer(question: str, chunks: list[str], context: dict) -> str:
    """无 LLM Key 时的兜底回答：基于检索片段 + 诊断数据组装。"""
    dims: dict = context.get("dimensions", {})
    weakest = min(dims.values(), key=lambda d: d["score"] / max(d["max"], 1), default=None)
    missing = context.get("missing_keywords", [])
    suggestions: list[str] = context.get("suggestions", [])
    score = context.get("score", "-")

    parts = [f"根据你的简历内容，我检索到与问题最相关的 {len(chunks)} 个片段。"]
    if weakest:
        parts.append(
            f"当前简历总分 {score}/100，其中「{weakest['label']}」是最薄弱维度"
            f"（{weakest['score']}/{weakest['max']}）。"
        )
    if missing:
        parts.append(f"针对目标岗位，简历还缺少这些关键词：{'、'.join(missing[:5])}，建议在项目描述和技能栏中自然补充。")
    if suggestions:
        parts.append("优先建议：" + "；".join(suggestions[:2]) + "。")
    if chunks:
        parts.append("与你问题最相关的简历原文：「" + chunks[0].replace("\n", " ")[:80] + "…」，建议围绕这段内容做针对性改写。")
    parts.append("（当前为规则引擎回答，配置 LLM_API_KEY 后可获得由大模型生成的个性化建议。）")
    return "\n\n".join(parts)


async def stream_answer(
    resume_text: str, question: str, context: dict
) -> AsyncGenerator[str, None]:
    """对外主入口：检索 → 生成 → 逐 token 流式产出。"""
    chunks, _ = await retrieve(resume_text, question)
    if settings.LLM_API_KEY:
        try:
            async for token in _stream_llm(build_prompt(question, chunks, context)):
                yield token
            return
        except Exception:
            pass  # LLM 不可用则落回规则回答
    # 规则兜底：逐句产出，模拟流式效果
    for sentence in _rule_answer(question, chunks, context).split("\n\n"):
        yield sentence
        await asyncio.sleep(0.15)


def sse_wrap(source: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """包装为 SSE 格式：data: {"token": "..."} 事件流。"""
    async def gen() -> AsyncGenerator[str, None]:
        async for token in source:
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return gen()
