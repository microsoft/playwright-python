from .base_llm_bot import BaseLLMBot
import time
from typing import List, Dict, Optional
import logging

class GoogleAIStudioBot(BaseLLMBot):
    """Google AI Studio机器人实现"""
    
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="google_ai_studio", log_level=log_level)
        
    def get_cookies(self) -> List[Dict]:
        """获取Google AI Studio的cookies并保存"""
        self.logger.info("正在获取Google AI Studio cookies...")
        try:
            self.page.goto("https://aistudio.google.com/prompts/new_chat")
            if not self._wait_for_selector("textarea"):
                raise Exception("页面加载超时")
                
            cookies = self.page.context.cookies()
            self.save_cookies(cookies)
            return cookies
        except Exception as e:
            self.logger.error(f"获取cookies失败: {str(e)}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], system_instruction: Optional[str] = None) -> Dict:
        """OpenAI兼容格式的chat接口
        
        Args:
            messages: OpenAI格式的消息列表，例如：
                     [{"role": "user", "content": "你好"},
                      {"role": "assistant", "content": "你好！"},
                      {"role": "user", "content": "今天天气如何？"}]
            system_instruction: 可选的系统提示词
            
        Returns:
            Dict: OpenAI兼容格式的响应
        """
        try:
            # 设置系统提示词
            if system_instruction:
                if not self._safe_fill_text('textarea[aria-label="System prompt"]', system_instruction):
                    raise Exception("设置系统提示词失败")
                self.logger.info(f"设置系统提示词: {system_instruction}")
            
            # 获取最后一条用户消息
            last_user_message = None
            for msg in reversed(messages):
                if msg["role"] == "user":
                    last_user_message = msg["content"]
                    break
            
            if not last_user_message:
                raise ValueError("未找到用户消息")
            
            # 发送消息
            if not self._safe_fill_text('textarea[aria-label="Chat input"]', last_user_message):
                raise Exception("发送消息失败")
            
            self.page.locator('textarea[aria-label="Chat input"]').press("Enter")
            self.logger.info(f"发送用户消息: {last_user_message}")
            
            # 等待AI响应
            if not self._wait_for_selector('[aria-label="Assistant response"]'):
                raise Exception("等待AI响应超时")
            
            time.sleep(2)  # 等待响应完整
            
            # 获取AI回复
            response = self.page.locator('[aria-label="Assistant response"]').last.text_content()
            self.logger.info(f"收到AI回复: {response}")
            
            # 记录对话
            self._append_to_history("user", last_user_message)
            self._append_to_history("assistant", response)
            
            # 保存对话历史
            self.save_conversation_history()
            
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response
                    }
                }]
            }
            
        except Exception as e:
            self.logger.error(f"对话过程中发生错误: {str(e)}")
            raise

def create_bot(log_level=logging.INFO) -> GoogleAIStudioBot:
    """创建GoogleAIStudioBot实例的工厂函数"""
    return GoogleAIStudioBot(log_level=log_level)

# 示例用法
if __name__ == "__main__":
    bot = create_bot()
    try:
        # 获取cookies
        cookies = bot.get_cookies()
        
        # OpenAI格式的对话示例
        messages = [
            {"role": "system", "content": "你是一个专业的AI助手，用中文回答问题，回答要简洁明了。"},
            {"role": "user", "content": "你好，请介绍一下你自己"},
        ]
        
        response = bot.chat(messages)
        print("\nAI回复:", response["choices"][0]["message"]["content"])
        
        # 继续对话
        messages.append(response["choices"][0]["message"])
        messages.append({"role": "user", "content": "你能帮我做些什么？"})
        
        response = bot.chat(messages)
        print("\nAI回复:", response["choices"][0]["message"]["content"])
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        bot.close()