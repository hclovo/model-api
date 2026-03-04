from fastapi import APIRouter, Depends

from model_api.dependencies import verify_api_key
from model_api.providers import list_all_models
from model_api.schemas import ModelListResponse

router = APIRouter()


@router.get("/models", response_model=ModelListResponse, dependencies=[Depends(verify_api_key)])
async def list_models():
    """列出所有可用模型。"""
    return ModelListResponse(data=list_all_models())