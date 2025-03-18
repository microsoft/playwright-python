from .base_job_bot import BaseJobBot, JobInfo
from typing import List, Dict, Optional
import logging
import json
import time
from datetime import datetime
import re

class GanjiBot(BaseJobBot):
    """赶集网职位爬虫"""
    
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="ganji", log_level=log_level)
        self.base_url = "https://www.ganji.com"
        
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
        try:
            # 构建搜索URL
            search_url = f"{self.base_url}/jobs/{city or 'beijing'}/zhaopin/?query={keyword}&page={page}"
            self.logger.info(f"搜索职位: {search_url}")
            
            # 访问搜索页面
            self.page.goto(search_url)
            if not self._wait_for_selector(".job-list"):
                raise Exception("加载职位列表超时")
            
            # 提取职位列表
            jobs = []
            job_elements = self.page.locator(".job-list .job-item").all()
            
            for job_elem in job_elements[:page_size]:
                try:
                    # 提取基本信息
                    title = job_elem.locator(".job-title").text_content()
                    company = job_elem.locator(".company-name").text_content()
                    salary = job_elem.locator(".salary").text_content()
                    location = job_elem.locator(".location").text_content()
                    url = job_elem.locator(".job-title a").get_attribute("href")
                    job_id = re.search(r"/job/(\d+)/", url).group(1)
                    
                    # 提取标签信息
                    tags = [tag.text_content() for tag in job_elem.locator(".job-tags .tag").all()]
                    
                    # 创建职位信息对象
                    job_info = JobInfo(
                        job_id=job_id,
                        title=title.strip(),
                        company=company.strip(),
                        salary=self._normalize_salary(salary.strip()),
                        location=location.strip(),
                        tags=tags,
                        url=url,
                        source="赶集网",
                        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    
                    jobs.append(job_info)
                    
                except Exception as e:
                    self.logger.error(f"提取职位信息失败: {str(e)}")
                    continue
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"搜索职位失败: {str(e)}")
            raise
    
    async def get_job_detail(self, job_id: str) -> JobInfo:
        """获取职位详情"""
        try:
            # 访问职位详情页
            detail_url = f"{self.base_url}/job/{job_id}/"
            self.page.goto(detail_url)
            
            if not self._wait_for_selector(".job-detail"):
                raise Exception("加载职位详情超时")
            
            # 提取详细信息
            title = self.page.locator(".job-title").text_content()
            company = self.page.locator(".company-name").text_content()
            salary = self.page.locator(".salary").text_content()
            location = self.page.locator(".location").text_content()
            description = self.page.locator(".job-description").text_content()
            
            # 提取公司信息
            company_type = self.page.locator(".company-type").text_content()
            company_size = self.page.locator(".company-size").text_content()
            
            # 提取要求信息
            requirements = self.page.locator(".job-requirements").text_content()
            experience = self._extract_work_years(requirements)
            education = self._extract_education(requirements)
            
            # 提取标签
            tags = [tag.text_content() for tag in self.page.locator(".job-tags .tag").all()]
            
            return JobInfo(
                job_id=job_id,
                title=title.strip(),
                company=company.strip(),
                salary=self._normalize_salary(salary.strip()),
                location=location.strip(),
                experience=experience,
                education=education,
                company_type=company_type.strip(),
                company_size=company_size.strip(),
                tags=tags,
                description=description.strip(),
                url=detail_url,
                source="赶集网",
                update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except Exception as e:
            self.logger.error(f"获取职位详情失败: {str(e)}")
            raise
    
    async def get_company_jobs(
        self,
        company_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[JobInfo]:
        """获取公司发布的职位列表"""
        try:
            # 访问公司职位列表页
            company_url = f"{self.base_url}/company/{company_id}/jobs/?page={page}"
            self.page.goto(company_url)
            
            if not self._wait_for_selector(".job-list"):
                raise Exception("加载公司职位列表超时")
            
            # 复用search_jobs的提取逻辑
            return await self.search_jobs(
                keyword="",
                page=page,
                page_size=page_size
            )
            
        except Exception as e:
            self.logger.error(f"获取公司职位列表失败: {str(e)}")
            raise
    
    def _normalize_salary(self, salary_text: str) -> str:
        """统一薪资格式"""
        # 移除多余空格和换行
        salary = re.sub(r'\s+', ' ', salary_text).strip()
        
        # 统一格式为"xxk-xxk/月"或"xx-xx万/年"
        if '千/月' in salary:
            salary = salary.replace('千/月', 'k/月')
        elif '万/月' in salary:
            salary = salary.replace('万/月', '0k/月')
        elif '万/年' in salary:
            salary = salary.replace('万/年', 'w/年')
            
        return salary
    
    def _extract_work_years(self, text: str) -> Optional[str]:
        """提取工作年限要求"""
        patterns = [
            r'(\d+[-\d]*年经验)',
            r'经验(\d+[-\d]*年)',
            r'应届生',
            r'不限经验'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    def _extract_education(self, text: str) -> Optional[str]:
        """提取学历要求"""
        education_levels = [
            '博士', '硕士', '本科', '大专',
            '高中', '中专', '初中及以下', '不限学历'
        ]
        
        for level in education_levels:
            if level in text:
                return level
        return None

def create_bot(log_level=logging.INFO) -> GanjiBot:
    """创建赶集网爬虫实例"""
    return GanjiBot(log_level=log_level)
