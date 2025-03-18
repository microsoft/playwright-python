from ..base_llm_bot import BaseLLMBot
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
from abc import abstractmethod

class JobInfo(BaseModel):
    """职位信息模型"""
    job_id: str
    title: str
    company: str
    salary: str
    location: str
    experience: Optional[str] = None
    education: Optional[str] = None
    company_type: Optional[str] = None
    company_size: Optional[str] = None
    tags: List[str] = []
    description: Optional[str] = None
    url: str
    source: str
    update_time: str

class BaseJobBot(BaseLLMBot):
    """招聘网站爬虫基类"""
    
    def __init__(self, site_name: str, log_level=logging.INFO):
        super().__init__(site_name=site_name, log_level=log_level)
        
    @abstractmethod
    async def search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        experience: Optional[str] = None,
        education: Optional[str] = None,
        salary_range: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> List[JobInfo]:
        """搜索职位"""
        pass
    
    @abstractmethod
    async def get_job_detail(self, job_id: str) -> JobInfo:
        """获取职位详情"""
        pass
    
    @abstractmethod
    async def get_company_jobs(
        self,
        company_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[JobInfo]:
        """获取公司发布的职位列表"""
        pass
    
    def _normalize_salary(self, salary_text: str) -> str:
        """统一薪资格式"""
        # 实现薪资格式标准化
        return salary_text
    
    def _extract_work_years(self, text: str) -> Optional[str]:
        """提取工作年限要求"""
        # 实现工作年限提取
        return text
    
    def _extract_education(self, text: str) -> Optional[str]:
        """提取学历要求"""
        # 实现学历要求提取
        return text

    async def analyze_job_requirements(self, job_info: JobInfo) -> Dict:
        """分析职位要求（使用LLM）"""
        try:
            prompt = f"""请分析这个职位的要求，包括：
            1. 技能要求
            2. 经验要求
            3. 教育背景
            4. 其他要求
            
            职位信息：
            标题：{job_info.title}
            描述：{job_info.description}
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的职位分析专家"},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.chat(messages)
            return {
                "job_id": job_info.job_id,
                "analysis": response["choices"][0]["message"]["content"]
            }
            
        except Exception as e:
            self.logger.error(f"分析职位要求失败: {str(e)}")
            raise
