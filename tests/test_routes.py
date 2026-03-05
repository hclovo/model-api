"""接口集成测试：直连本地服务 http://127.0.0.1:8000，运行前需先启动服务。"""
import json
import pytest


# ── 辅助 ──────────────────────────────────────────────────────────────────────

def _chat_payload(**kwargs) -> dict:
    return {
        "model": "gemini-2.0-flash",
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        **kwargs,
    }


def _parse_sse(text: str) -> list[dict]:
    """将 SSE 响应体解析为 chunk 字典列表（跳过 [DONE]）。"""
    return [
        json.loads(line[6:])
        for line in text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


# ── /health ───────────────────────────────────────────────────────────────────

async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── /v1/models ────────────────────────────────────────────────────────────────

async def test_list_models_status(client):
    resp = await client.get("/v1/models")
    assert resp.status_code == 200


async def test_list_models_structure(client):
    data = (await client.get("/v1/models")).json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


async def test_list_models_contains_gemini(client):
    data = (await client.get("/v1/models")).json()
    ids = [m["id"] for m in data["data"]]
    assert "gemini-2.0-flash" in ids


async def test_list_models_item_fields(client):
    data = (await client.get("/v1/models")).json()
    model = data["data"][0]
    assert "id" in model
    assert "object" in model
    assert model["object"] == "model"


# ── /v1/chat/completions（非流式）────────────────────────────────────────────

async def test_chat_status(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload())
    assert resp.status_code == 200


async def test_chat_response_object(client):
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    assert data["object"] == "chat.completion"


async def test_chat_response_id(client):
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    assert data["id"].startswith("chatcmpl-")


async def test_chat_response_model_matches_request(client):
    """响应中的 model 字段应与请求一致，不含 provider 前缀。"""
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    assert data["model"] == "gemini-2.0-flash"


async def test_chat_response_choices(client):
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    assert len(data["choices"]) > 0
    choice = data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert isinstance(choice["message"]["content"], str)
    assert len(choice["message"]["content"]) > 0


async def test_chat_response_finish_reason(client):
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    assert data["choices"][0]["finish_reason"] is not None


async def test_chat_response_usage(client):
    data = (await client.post("/v1/chat/completions", json=_chat_payload())).json()
    usage = data["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


async def test_chat_with_system_message(client):
    payload = _chat_payload(messages=[
        {"role": "system", "content": "你是一个专业助手，回答要简洁"},
        {"role": "user", "content": "1+1等于几"},
    ])
    resp = await client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"]


async def test_chat_with_temperature(client):
    resp = await client.post(
        "/v1/chat/completions",
        json=_chat_payload(temperature=0.5, max_tokens=50),
    )
    assert resp.status_code == 200


async def test_chat_missing_messages(client):
    resp = await client.post("/v1/chat/completions", json={"model": "gemini-2.0-flash"})
    assert resp.status_code == 422


async def test_chat_missing_model(client):
    resp = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 422


async def test_chat_invalid_role(client):
    resp = await client.post(
        "/v1/chat/completions",
        json={"model": "gemini-2.0-flash", "messages": [{"role": "bad_role", "content": "hi"}]},
    )
    assert resp.status_code == 422


# ── /v1/chat/completions（流式）──────────────────────────────────────────────

async def test_chat_stream_status(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    assert resp.status_code == 200


async def test_chat_stream_content_type(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    assert "text/event-stream" in resp.headers["content-type"]


async def test_chat_stream_ends_with_done(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    assert "data: [DONE]" in resp.text


async def test_chat_stream_chunks_structure(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    chunks = _parse_sse(resp.text)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk["object"] == "chat.completion.chunk"
        assert "choices" in chunk
        assert len(chunk["choices"]) > 0


async def test_chat_stream_has_content(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    chunks = _parse_sse(resp.text)
    content = "".join(
        c["choices"][0]["delta"].get("content") or ""
        for c in chunks
    )
    assert len(content) > 0


async def test_chat_stream_no_null_role_in_delta(client):
    """delta 中若无 role，则不应出现 null 值（符合 OpenAI SSE 规范）。"""
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    chunks = _parse_sse(resp.text)
    for chunk in chunks:
        delta = chunk["choices"][0]["delta"]
        assert "role" not in delta or delta["role"] is not None


async def test_chat_stream_last_chunk_has_finish_reason(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    chunks = _parse_sse(resp.text)
    finish_reasons = [
        c["choices"][0].get("finish_reason")
        for c in chunks
        if c["choices"][0].get("finish_reason")
    ]
    assert len(finish_reasons) > 0


async def test_chat_stream_no_cache_header(client):
    resp = await client.post("/v1/chat/completions", json=_chat_payload(stream=True))
    assert resp.headers.get("cache-control") == "no-cache"
