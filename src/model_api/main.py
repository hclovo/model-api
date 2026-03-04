import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from model_api.config import settings
from model_api.routes.chat import router as chat_router
from model_api.routes.models import router as models_router

app = FastAPI(
    title="Model API Gateway",
    description="多模型 API 网关，OpenAI 兼容接口，支持 Gemini / OpenAI 等",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
