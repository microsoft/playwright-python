from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional
import logging
from services.job_service import JobService
from bots.base_job_bot import JobInfo

router = APIRouter()
logger = logging.getLogger("job_search")

class JobSearchRequest(BaseModel):
    """职位搜索请求模型"""
    keyword: str
    city: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    salary_range: Optional[str] = None
    platform: str = "all"  # "all", "ganji", "boss"
    page: int = 1
    page_size: int = 20

class JobAnalysisRequest(BaseModel):
    """职位分析请求模型"""
    job_id: str
    platform: str

@router.post("/search", response_model=List[JobInfo])
async def search_jobs(request: JobSearchRequest):
    """搜索职位"""
    try:
        job_service = JobService()
        return await job_service.search_jobs(
            keyword=request.keyword,
            city=request.city,
            experience=request.experience,
            education=request.education,
            salary_range=request.salary_range,
            platform=request.platform,
            page=request.page,
            page_size=request.page_size
        )
    except Exception as e:
        logger.error(f"搜索职位失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail/{platform}/{job_id}", response_model=JobInfo)
async def get_job_detail(platform: str, job_id: str):
    """获取职位详情"""
    try:
        job_service = JobService()
        return await job_service.get_job_detail(platform, job_id)
    except Exception as e:
        logger.error(f"获取职位详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company/{platform}/{company_id}/jobs", response_model=List[JobInfo])
async def get_company_jobs(
    platform: str,
    company_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取公司发布的职位列表"""
    try:
        job_service = JobService()
        return await job_service.get_company_jobs(
            platform,
            company_id,
            page,
            page_size
        )
    except Exception as e:
        logger.error(f"获取公司职位列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_job(request: JobAnalysisRequest):
    """分析职位要求"""
    try:
        job_service = JobService()
        return await job_service.analyze_job(
            platform=request.platform,
            job_id=request.job_id
        )
    except Exception as e:
        logger.error(f"分析职位失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
