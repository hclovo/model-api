import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from model_api.dependencies import verify_api_key
from model_api.providers import get_provider
from model_api.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post(
    "/chat/completions",
    response_model=ChatResponse,
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

    # 流式：SSE 格式
    async def event_stream():
        try:
            async for chunk in provider.chat_stream(request):
                data = chunk.model_dump_json(exclude_none=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            error = json.dumps({"error": {"message": str(e), "type": "server_error"}})
            yield f"data: {error}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")