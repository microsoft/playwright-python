from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Union
from pathlib import Path
from abc import ABC, abstractmethod

class BaseLLMBot(ABC):
    """LLM机器人基类，提供通用功能实现"""
    
    def __init__(self, site_name: str, log_level=logging.INFO):
        """
        初始化基类
        
        Args:
            site_name: 站点名称，用于区分不同的实现
            log_level: 日志级别
        """
        self.site_name = site_name
        self.base_dir = Path(__file__).parent
        self.setup_directories()
        self.setup_logging(log_level)
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.conversation_history = []
        
    def setup_directories(self):
        """创建必要的目录结构"""
        dirs = ['cookies', 'logs', 'history']
        for dir_name in dirs:
            dir_path = self.base_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            
    def setup_logging(self, log_level):
        """设置日志系统"""
        self.logger = logging.getLogger(self.site_name)
        self.logger.setLevel(log_level)
        
        # 文件处理器 - 详细日志
        log_file = self.base_dir / 'logs' / f'{self.site_name}_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器 - 简要信息
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def save_cookies(self, cookies: List[Dict]) -> None:
        """保存cookies到文件
        
        Args:
            cookies: 要保存的cookies列表
        """
        cookie_file = self.base_dir / 'cookies' / f'{self.site_name}_cookies.json'
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Cookies已保存到: {cookie_file}")

    def load_cookies(self) -> bool:
        """从文件加载cookies
        
        Returns:
            bool: 是否成功加载cookies
        """
        cookie_file = self.base_dir / 'cookies' / f'{self.site_name}_cookies.json'
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                self.context.add_cookies(cookies)
                self.logger.info("成功加载cookies")
                return True
            except Exception as e:
                self.logger.error(f"加载cookies失败: {str(e)}")
                return False
        return False

    def save_conversation_history(self):
        """将对话历史保存为Markdown格式"""
        if not self.conversation_history:
            return
            
        history_file = self.base_dir / 'history' / f'{self.site_name}_conversation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        
        with open(history_file, 'w', encoding='utf-8') as f:
            f.write(f"# {self.site_name} 对话记录\n\n")
            f.write(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for msg in self.conversation_history:
                role = "🧑 用户" if msg["role"] == "user" else "🤖 助手"
                f.write(f"### {role}\n\n{msg['content']}\n\n")
                
        self.logger.info(f"对话历史已保存到: {history_file}")

    def close(self):
        """关闭浏览器和playwright"""
        try:
            self.context.close()
            self.browser.close()
            self.playwright.stop()
            self.logger.info("已关闭浏览器和playwright")
        except Exception as e:
            self.logger.error(f"关闭过程中发生错误: {str(e)}")

    @abstractmethod
    def get_cookies(self) -> List[Dict]:
        """获取站点cookies的抽象方法"""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], system_instruction: Optional[str] = None) -> Dict:
        """OpenAI兼容格式的chat接口抽象方法"""
        pass

    def _append_to_history(self, role: str, content: str):
        """添加消息到对话历史
        
        Args:
            role: 消息角色 ("user" 或 "assistant")
            content: 消息内容
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def _wait_for_selector(self, selector: str, timeout: int = 30000) -> bool:
        """等待元素出现
        
        Args:
            selector: 要等待的元素选择器
            timeout: 超时时间（毫秒）
            
        Returns:
            bool: 是否成功等待到元素
        """
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.error(f"等待元素 {selector} 超时: {str(e)}")
            return False

    def _safe_fill_text(self, selector: str, text: str) -> bool:
        """安全地填充文本
        
        Args:
            selector: 元素选择器
            text: 要填充的文本
            
        Returns:
            bool: 是否成功填充
        """
        try:
            element = self.page.locator(selector)
            element.fill(text)
            return True
        except Exception as e:
            self.logger.error(f"填充文本失败: {str(e)}")
            return False
