from .base_job_bot import BaseJobBot, JobInfo
from typing import List, Dict, Optional
import logging
import json
import time
from datetime import datetime
import re

class BossBot(BaseJobBot):
    """BOSS直聘职位爬虫"""
    
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="boss", log_level=log_level)
        self.base_url = "https://www.zhipin.com"
        
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
            city_code = self._get_city_code(city or 'beijing')
            search_url = f"{self.base_url}/web/geek/job?query={keyword}&city={city_code}&page={page}"
            self.logger.info(f"搜索职位: {search_url}")
            
            # 访问搜索页面
            self.page.goto(search_url)
            if not self._wait_for_selector(".job-list-box"):
                raise Exception("加载职位列表超时")
            
            # 提取职位列表
            jobs = []
            job_elements = self.page.locator(".job-list-box .job-primary").all()
            
            for job_elem in job_elements[:page_size]:
                try:
                    # 提取基本信息
                    title = job_elem.locator(".job-name").text_content()
                    company = job_elem.locator(".company-name").text_content()
                    salary = job_elem.locator(".salary").text_content()
                    location = job_elem.locator(".job-area").text_content()
                    
                    # 提取URL和职位ID
                    url = job_elem.locator(".job-name a").get_attribute("href")
                    job_id = re.search(r"/job_detail/([^?]+)", url).group(1)
                    
                    # 提取公司信息
                    company_info = job_elem.locator(".company-text p").text_content()
                    company_type, company_size = self._parse_company_info(company_info)
                    
                    # 提取要求信息
                    requirements = job_elem.locator(".job-limit").text_content()
                    experience = self._extract_work_years(requirements)
                    education = self._extract_education(requirements)
                    
                    # 提取标签
                    tags = [tag.text_content() for tag in job_elem.locator(".tags .tag-item").all()]
                    
                    # 创建职位信息对象
                    job_info = JobInfo(
                        job_id=job_id,
                        title=title.strip(),
                        company=company.strip(),
                        salary=self._normalize_salary(salary.strip()),
                        location=location.strip(),
                        experience=experience,
                        education=education,
                        company_type=company_type,
                        company_size=company_size,
                        tags=tags,
                        url=f"{self.base_url}{url}",
                        source="BOSS直聘",
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
            detail_url = f"{self.base_url}/job_detail/{job_id}"
            self.page.goto(detail_url)
            
            if not self._wait_for_selector(".job-detail"):
                raise Exception("加载职位详情超时")
            
            # 提取详细信息
            title = self.page.locator(".job-primary .name").text_content()
            company = self.page.locator(".company-info .name").text_content()
            salary = self.page.locator(".salary").text_content()
            location = self.page.locator(".job-primary .address").text_content()
            description = self.page.locator(".job-sec .text").text_content()
            
            # 提取公司信息
            company_info = self.page.locator(".company-info p").text_content()
            company_type, company_size = self._parse_company_info(company_info)
            
            # 提取要求信息
            requirements = self.page.locator(".job-primary .info-primary p").text_content()
            experience = self._extract_work_years(requirements)
            education = self._extract_education(requirements)
            
            # 提取标签
            tags = [tag.text_content() for tag in self.page.locator(".tags .tag-item").all()]
            
            return JobInfo(
                job_id=job_id,
                title=title.strip(),
                company=company.strip(),
                salary=self._normalize_salary(salary.strip()),
                location=location.strip(),
                experience=experience,
                education=education,
                company_type=company_type,
                company_size=company_size,
                tags=tags,
                description=description.strip(),
                url=detail_url,
                source="BOSS直聘",
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
            company_url = f"{self.base_url}/gongsi/{company_id}?page={page}"
            self.page.goto(company_url)
            
            if not self._wait_for_selector(".job-list-box"):
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
    
    def _get_city_code(self, city_name: str) -> str:
        """获取城市代码"""
        # 这里应该维护一个城市代码映射表
        city_codes = {
            'beijing': '101010100',
            'shanghai': '101020100',
            'guangzhou': '101280100',
            'shenzhen': '101280600'
        }
        return city_codes.get(city_name.lower(), '101010100')  # 默认北京
    
    def _parse_company_info(self, info_text: str) -> tuple:
        """解析公司信息"""
        company_type = ""
        company_size = ""
        
        if "·" in info_text:
            parts = info_text.split("·")
            if len(parts) >= 2:
                company_type = parts[0].strip()
                company_size = parts[-1].strip()
                
        return company_type, company_size
    
    def _normalize_salary(self, salary_text: str) -> str:
        """统一薪资格式"""
        # BOSS直聘的薪资一般是"XXk-YYk"格式
        salary = re.sub(r'\s+', '', salary_text).strip()
        
        # 统一为"xx-xxk/月"格式
        if '·' in salary:
            salary = salary.split('·')[0]
        
        if not salary.endswith('/月'):
            salary += '/月'
            
        return salary
    
    def _extract_work_years(self, text: str) -> Optional[str]:
        """提取工作年限要求"""
        patterns = [
            r'(\d+[-\d]*年经验)',
            r'经验(\d+[-\d]*年)',
            r'应届生',
            r'经验不限'
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
            '高中', '中专', '初中及以下', '学历不限'
        ]
        
        for level in education_levels:
            if level in text:
                return level
        return None

def create_bot(log_level=logging.INFO) -> BossBot:
    """创建BOSS直聘爬虫实例"""
    return BossBot(log_level=log_level)
