import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from model_api.dependencies import verify_api_key
from model_api.providers import get_provider
from model_api.schemas import ChatRequest, ChatResponse, ErrorDetail, ErrorResponse

router = APIRouter()


@router.post(
    "/chat/completions",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
)
async def chat_completions(request: ChatRequest):
    """OpenAI 兼容的对话接口，支持流式与非流式。"""
    try:
        provider = get_provider(request.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not request.stream:
        return await provider.chat(request)

    async def event_stream():
        try:
            async for chunk in provider.chat_stream(request):
                chunk_dict = chunk.model_dump()
                # delta 只输出有值的字段：role 仅在第一个 chunk 出现，
                # content 为 None 时不输出（符合 OpenAI SSE 规范）
                for c in chunk_dict.get("choices", []):
                    c["delta"] = {k: v for k, v in c["delta"].items() if v is not None}
                yield f"data: {json.dumps(chunk_dict, ensure_ascii=False)}\n\n"
        except Exception as e:
            err = ErrorResponse(error=ErrorDetail(message=str(e)))
            yield f"data: {err.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲，保证流式实时输出
        },
    )
