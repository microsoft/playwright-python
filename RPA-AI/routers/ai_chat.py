from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from core.config import settings
from services.llm_service import LLMService
from services.response_processor import ResponseProcessor

router = APIRouter()
logger = logging.getLogger("ai_chat")

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    system_instruction: Optional[str] = None
    llm_provider: str = "google_ai_studio"  # 默认使用Google AI Studio

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """处理聊天请求"""
    try:
        # 获取LLM服务实例
        llm_service = LLMService.get_instance(request.llm_provider)
        
        # 发送消息并获取响应
        response = await llm_service.send_message(
            messages=request.messages,
            system_instruction=request.system_instruction
        )
        
        # 后台任务：保存对话历史
        background_tasks.add_task(
            llm_service.save_conversation,
            response["conversation_id"]
        )
        
        return ChatResponse(
            response=response["message"],
            conversation_id=response["conversation_id"]
        )
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
