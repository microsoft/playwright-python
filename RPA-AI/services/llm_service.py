from typing import Dict, List, Optional
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from google_ai_studio import GoogleAIStudioBot
from core.config import settings
import uuid

logger = logging.getLogger("llm_service")

class LLMService:
    """LLM服务管理器"""
    
    _instances: Dict[str, "LLMService"] = {}
    _executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
    
    def __init__(self, provider: str):
        self.provider = provider
        self.bot = None
        self.conversations: Dict[str, List] = {}
        
    @classmethod
    def get_instance(cls, provider: str) -> "LLMService":
        """获取服务实例（单例模式）"""
        if provider not in cls._instances:
            cls._instances[provider] = cls(provider)
        return cls._instances[provider]
    
    def _ensure_bot(self):
        """确保bot已初始化"""
        if self.bot is None:
            if self.provider == "google_ai_studio":
                self.bot = GoogleAIStudioBot()
                # 尝试加载cookies
                self.bot.load_cookies()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def send_message(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None
    ) -> Dict:
        """发送消息到LLM（异步）"""
        try:
            self._ensure_bot()
            
            # 生成会话ID
            conversation_id = str(uuid.uuid4())
            
            # 在线程池中执行阻塞操作
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._send_message_sync,
                messages,
                system_instruction
            )
            
            # 保存会话历史
            self.conversations[conversation_id] = messages + [{
                "role": "assistant",
                "content": response["choices"][0]["message"]["content"]
            }]
            
            return {
                "message": response["choices"][0]["message"]["content"],
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    def _send_message_sync(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None
    ) -> Dict:
        """同步发送消息（在线程池中执行）"""
        return self.bot.chat(messages, system_instruction)
    
    async def save_conversation(self, conversation_id: str):
        """保存对话历史（后台任务）"""
        if conversation_id in self.conversations:
            try:
                self._ensure_bot()
                messages = self.conversations[conversation_id]
                self.bot.conversation_history = messages
                self.bot.save_conversation_history()
            except Exception as e:
                logger.error(f"Error saving conversation: {str(e)}")
    
    def close(self):
        """关闭服务"""
        if self.bot:
            self.bot.close()
            self.bot = None
