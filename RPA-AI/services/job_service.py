from typing import List, Dict, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bots.ganji_bot import GanjiBot
from bots.boss_bot import BossBot
from bots.base_job_bot import JobInfo
from core.config import settings

logger = logging.getLogger("job_service")

class JobService:
    """职位服务类"""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
        self._bots = {}
        
    def _get_bot(self, platform: str):
        """获取对应平台的爬虫实例"""
        if platform not in self._bots:
            if platform == "ganji":
                self._bots[platform] = GanjiBot()
            elif platform == "boss":
                self._bots[platform] = BossBot()
            else:
                raise ValueError(f"不支持的平台: {platform}")
        return self._bots[platform]
    
    async def search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        experience: Optional[str] = None,
        education: Optional[str] = None,
        salary_range: Optional[str] = None,
        platform: str = "all",
        page: int = 1,
        page_size: int = 20
    ) -> List[JobInfo]:
        """搜索职位"""
        try:
            if platform == "all":
                # 并发搜索所有平台
                tasks = []
                for p in ["ganji", "boss"]:
                    bot = self._get_bot(p)
                    task = asyncio.create_task(bot.search_jobs(
                        keyword=keyword,
                        city=city,
                        experience=experience,
                        education=education,
                        salary_range=salary_range,
                        page=page,
                        page_size=page_size
                    ))
                    tasks.append(task)
                
                # 等待所有任务完成
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 合并结果
                all_jobs = []
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"搜索职位失败: {str(result)}")
                    else:
                        all_jobs.extend(result)
                
                return all_jobs
            else:
                # 搜索单个平台
                bot = self._get_bot(platform)
                return await bot.search_jobs(
                    keyword=keyword,
                    city=city,
                    experience=experience,
                    education=education,
                    salary_range=salary_range,
                    page=page,
                    page_size=page_size
                )
                
        except Exception as e:
            logger.error(f"搜索职位失败: {str(e)}")
            raise
    
    async def get_job_detail(self, platform: str, job_id: str) -> JobInfo:
        """获取职位详情"""
        try:
            bot = self._get_bot(platform)
            return await bot.get_job_detail(job_id)
        except Exception as e:
            logger.error(f"获取职位详情失败: {str(e)}")
            raise
    
    async def get_company_jobs(
        self,
        platform: str,
        company_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[JobInfo]:
        """获取公司发布的职位列表"""
        try:
            bot = self._get_bot(platform)
            return await bot.get_company_jobs(
                company_id=company_id,
                page=page,
                page_size=page_size
            )
        except Exception as e:
            logger.error(f"获取公司职位列表失败: {str(e)}")
            raise
    
    async def analyze_job(self, platform: str, job_id: str) -> Dict:
        """分析职位要求"""
        try:
            # 获取职位详情
            job_info = await self.get_job_detail(platform, job_id)
            
            # 使用LLM分析职位要求
            bot = self._get_bot(platform)
            return await bot.analyze_job_requirements(job_info)
            
        except Exception as e:
            logger.error(f"分析职位失败: {str(e)}")
            raise
    
    def close(self):
        """关闭所有爬虫实例"""
        for bot in self._bots.values():
            try:
                bot.close()
            except Exception as e:
                logger.error(f"关闭爬虫失败: {str(e)}")
        self._bots.clear()
