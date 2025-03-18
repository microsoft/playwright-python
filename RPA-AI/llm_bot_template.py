from .base_llm_bot import BaseLLMBot
import time
from typing import List, Dict, Optional
import logging

class NewLLMBot(BaseLLMBot):
    """新的LLM机器人实现模板"""
    
    def __init__(self, log_level=logging.INFO):
        # 修改site_name为对应的站点名称
        super().__init__(site_name="new_llm_site", log_level=log_level)
        
    def get_cookies(self) -> List[Dict]:
        """获取站点cookies并保存"""
        self.logger.info("正在获取cookies...")
        try:
            # 1. 访问目标网站
            self.page.goto("https://your-site-url.com")
            
            # 2. 等待必要的页面元素加载
            if not self._wait_for_selector("your-selector"):
                raise Exception("页面加载超时")
                
            # 3. 获取并保存cookies
            cookies = self.page.context.cookies()
            self.save_cookies(cookies)
            return cookies
        except Exception as e:
            self.logger.error(f"获取cookies失败: {str(e)}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], system_instruction: Optional[str] = None) -> Dict:
        """OpenAI兼容格式的chat接口
        
        Args:
            messages: OpenAI格式的消息列表
            system_instruction: 可选的系统提示词
            
        Returns:
            Dict: OpenAI兼容格式的响应
        """
        try:
            # 1. 处理系统提示词（如果支持）
            if system_instruction:
                if not self._safe_fill_text('system-prompt-selector', system_instruction):
                    raise Exception("设置系统提示词失败")
                self.logger.info(f"设置系统提示词: {system_instruction}")
            
            # 2. 获取最后一条用户消息
            last_user_message = None
            for msg in reversed(messages):
                if msg["role"] == "user":
                    last_user_message = msg["content"]
                    break
            
            if not last_user_message:
                raise ValueError("未找到用户消息")
            
            # 3. 发送消息
            if not self._safe_fill_text('chat-input-selector', last_user_message):
                raise Exception("发送消息失败")
            
            # 4. 触发发送（根据实际情况修改）
            self.page.locator('send-button-selector').click()
            self.logger.info(f"发送用户消息: {last_user_message}")
            
            # 5. 等待并获取AI响应
            if not self._wait_for_selector('response-selector'):
                raise Exception("等待AI响应超时")
            
            time.sleep(2)  # 等待响应完整
            
            # 6. 获取回复内容
            response = self.page.locator('response-selector').last.text_content()
            self.logger.info(f"收到AI回复: {response}")
            
            # 7. 记录对话
            self._append_to_history("user", last_user_message)
            self._append_to_history("assistant", response)
            
            # 8. 保存对话历史
            self.save_conversation_history()
            
            # 9. 返回OpenAI格式的响应
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

def create_bot(log_level=logging.INFO) -> NewLLMBot:
    """创建NewLLMBot实例的工厂函数"""
    return NewLLMBot(log_level=log_level)

# 使用示例
if __name__ == "__main__":
    bot = create_bot()
    try:
        # 获取cookies
        cookies = bot.get_cookies()
        
        # OpenAI格式的对话示例
        messages = [
            {"role": "system", "content": "系统提示词"},
            {"role": "user", "content": "用户消息"},
        ]
        
        response = bot.chat(messages)
        print("\nAI回复:", response["choices"][0]["message"]["content"])
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        bot.close()
