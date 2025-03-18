from typing import List, Dict, Optional
import logging
from datetime import datetime
from ..base_llm_bot import BaseLLMBot

class SurveyGenerator(BaseLLMBot):
    """智能问卷生成器"""
    
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="survey", log_level=log_level)
        self.questions = []
        self.conversation_history = []
        
    async def analyze_user_query(self, query: str) -> Dict:
        """分析用户问题并生成必要的问题列表"""
        try:
            prompt = f"""作为一个专业的用户研究专家，请分析以下用户问题，并提供需要收集的信息：

用户问题：{query}

请提供：
1. 必要的问题列表
2. 每个问题的类型（单选、多选、文本等）
3. 问题的优先级
4. 提问的语气和方式建议
5. 可能的跳转逻辑

注意：
- 问题要简短清晰
- 使用友好的语气
- 考虑移动端体验
- 避免敏感信息
"""
            
            messages = [
                {"role": "system", "content": "你是一个专业的用户研究专家，擅长设计友好的问卷。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.chat(messages)
            analysis = response["choices"][0]["message"]["content"]
            
            # 解析问题列表
            questions = await self._parse_questions(analysis)
            self.questions = questions
            
            return {
                "original_query": query,
                "analysis": analysis,
                "questions": questions,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"分析用户问题失败: {str(e)}")
            raise
            
    async def generate_question_prompt(self, question: Dict, user_info: Optional[Dict] = None) -> str:
        """生成友好的问题提示语"""
        try:
            context = f"""
问题信息：
{question}

用户信息：
{user_info if user_info else '新用户'}

请生成：
1. 友好的问题提示语
2. 适当的表情符号
3. 鼓励性的文案
4. 填写建议（如果需要）

要求：
- 语气要自然友好
- 适当使用表情
- 突出价值和意义
- 尊重用户时间
"""
            
            messages = [
                {"role": "system", "content": "你是一个亲和力极强的用户交流专家。"},
                {"role": "user", "content": context}
            ]
            
            response = await self.chat(messages)
            prompt = response["choices"][0]["message"]["content"]
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"生成问题提示语失败: {str(e)}")
            raise
            
    async def _parse_questions(self, analysis: str) -> List[Dict]:
        """解析LLM返回的问题分析结果"""
        try:
            prompt = f"""请将以下问卷分析结果转换为结构化的问题列表：

{analysis}

每个问题需包含：
1. id: 唯一标识
2. type: 问题类型（text/radio/checkbox/number）
3. title: 问题标题
4. required: 是否必填
5. options: 选项列表（如果适用）
6. priority: 优先级（1-5）
7. skip_logic: 跳转逻辑（如果适用）

请以JSON格式返回。"""

            messages = [
                {"role": "system", "content": "你是一个问卷设计专家。"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.chat(messages)
            questions = eval(response["choices"][0]["message"]["content"])
            
            return questions
            
        except Exception as e:
            self.logger.error(f"解析问题失败: {str(e)}")
            raise
            
    def save_response(self, question_id: str, answer: str, user_info: Optional[Dict] = None):
        """保存用户回答"""
        try:
            response = {
                "question_id": question_id,
                "answer": answer,
                "user_info": user_info,
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存到数据库或文件
            self._save_to_storage(response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"保存回答失败: {str(e)}")
            raise
            
    def _save_to_storage(self, response: Dict):
        """保存响应到存储"""
        # TODO: 实现具体的存储逻辑
        pass
