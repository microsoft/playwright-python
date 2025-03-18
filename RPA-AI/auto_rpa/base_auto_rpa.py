from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import json
from datetime import datetime
from bs4 import BeautifulSoup
import re
from ..base_llm_bot import BaseLLMBot

class AutoRPABot(BaseLLMBot):
    """智能RPA机器人基类"""
    
    def __init__(self, site_name: str, log_level=logging.INFO):
        super().__init__(site_name=site_name, log_level=log_level)
        self.html_analysis = None
        self.generated_script = None
        self.execution_plan = None
        
    async def analyze_page(self, html_content: str, task_goal: str, workflow: Optional[str] = None) -> Dict:
        """分析页面结构并生成操作计划
        
        Args:
            html_content: 网页源码
            task_goal: 任务目标描述
            workflow: 可选的操作流程描述
        """
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 准备分析提示
            prompt = f"""作为网页自动化专家，请分析以下网页结构并提供详细的操作计划：

任务目标：{task_goal}

{"操作流程：" + workflow if workflow else ""}

网页结构分析：
1. 表单和输入字段：
{self._analyze_forms(soup)}

2. 按钮和交互元素：
{self._analyze_buttons(soup)}

3. 数据展示区域：
{self._analyze_data_areas(soup)}

请提供：
1. 关键元素的选择器
2. 详细的操作步骤
3. 可能需要的等待条件
4. 数据提取方法
5. 错误处理建议"""

            # 调用LLM进行分析
            messages = [
                {"role": "system", "content": "你是一个网页自动化专家，精通Playwright和网页结构分析。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.chat(messages)
            analysis = response["choices"][0]["message"]["content"]
            
            # 保存分析结果
            self.html_analysis = {
                "task_goal": task_goal,
                "workflow": workflow,
                "analysis": analysis,
                "timestamp": datetime.now().isoformat()
            }
            
            return self.html_analysis
            
        except Exception as e:
            self.logger.error(f"页面分析失败: {str(e)}")
            raise
            
    async def generate_script(self) -> str:
        """根据分析结果生成自动化脚本"""
        if not self.html_analysis:
            raise ValueError("请先调用analyze_page进行页面分析")
            
        try:
            prompt = f"""基于以下页面分析结果，生成完整的Playwright自动化脚本：

分析结果：
{self.html_analysis['analysis']}

要求：
1. 使用Python和Playwright
2. 包含完整的错误处理
3. 添加详细的日志记录
4. 使用强大的选择器
5. 包含重试机制
6. 添加注释说明

请生成完整的Python类实现。"""

            messages = [
                {"role": "system", "content": "你是一个Python自动化专家，精通Playwright脚本开发。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.chat(messages)
            script = response["choices"][0]["message"]["content"]
            
            # 保存生成的脚本
            self.generated_script = script
            
            # 将脚本保存到文件
            script_file = self.base_dir / 'generated_scripts' / f'{self.site_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
            script_file.parent.mkdir(exist_ok=True)
            
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script)
                
            self.logger.info(f"脚本已生成并保存到: {script_file}")
            
            return script
            
        except Exception as e:
            self.logger.error(f"生成脚本失败: {str(e)}")
            raise
            
    async def execute_script(self, url: str, cookies: List[Dict]) -> Dict:
        """执行生成的脚本
        
        Args:
            url: 目标URL
            cookies: Cookie列表
        """
        if not self.generated_script:
            raise ValueError("请先调用generate_script生成脚本")
            
        try:
            # 设置cookies
            self.page.goto(url)
            self.context.add_cookies(cookies)
            
            # 执行生成的脚本
            exec(self.generated_script)
            
            return {"status": "success", "message": "脚本执行完成"}
            
        except Exception as e:
            self.logger.error(f"执行脚本失败: {str(e)}")
            raise
            
    def _analyze_forms(self, soup: BeautifulSoup) -> str:
        """分析页面中的表单和输入字段"""
        forms = []
        
        # 分析表单
        for form in soup.find_all('form'):
            form_info = {
                'id': form.get('id', ''),
                'name': form.get('name', ''),
                'action': form.get('action', ''),
                'method': form.get('method', ''),
                'inputs': []
            }
            
            # 分析输入字段
            for input_field in form.find_all(['input', 'select', 'textarea']):
                input_info = {
                    'type': input_field.get('type', 'text'),
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'placeholder': input_field.get('placeholder', '')
                }
                form_info['inputs'].append(input_info)
                
            forms.append(form_info)
            
        return json.dumps(forms, indent=2, ensure_ascii=False)
        
    def _analyze_buttons(self, soup: BeautifulSoup) -> str:
        """分析页面中的按钮和交互元素"""
        buttons = []
        
        # 查找所有按钮
        for button in soup.find_all(['button', 'a', 'input[type="button"]', 'input[type="submit"]']):
            button_info = {
                'type': button.name,
                'id': button.get('id', ''),
                'class': button.get('class', []),
                'text': button.text.strip(),
                'onclick': button.get('onclick', '')
            }
            buttons.append(button_info)
            
        return json.dumps(buttons, indent=2, ensure_ascii=False)
        
    def _analyze_data_areas(self, soup: BeautifulSoup) -> str:
        """分析页面中的数据展示区域"""
        data_areas = []
        
        # 查找可能的数据展示区域
        for area in soup.find_all(['table', 'div.list', 'div.data', 'ul.list']):
            area_info = {
                'type': area.name,
                'id': area.get('id', ''),
                'class': area.get('class', []),
                'children_count': len(area.find_all()),
                'data_attributes': {k:v for k,v in area.attrs.items() if 'data-' in k}
            }
            data_areas.append(area_info)
            
        return json.dumps(data_areas, indent=2, ensure_ascii=False)
