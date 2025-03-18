from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
import logging
from datetime import datetime

# 导入路由模块
from routers import ai_chat, job_search, company_info, recruitment_analysis
from core.config import settings
from core.logging_config import setup_logging

# 创建FastAPI应用
app = FastAPI(
    title="智能信息助手API",
    description="提供AI对话、职位查询、企业信息和招聘分析等智能服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ai_chat.router, prefix="/api/v1/chat", tags=["AI对话"])
app.include_router(job_search.router, prefix="/api/v1/jobs", tags=["职位查询"])
app.include_router(company_info.router, prefix="/api/v1/companies", tags=["企业信息"])
app.include_router(recruitment_analysis.router, prefix="/api/v1/analysis", tags=["招聘分析"])

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    # 设置日志
    setup_logging()
    
    # 创建必要的目录
    for dir_name in ['logs', 'data', 'cache']:
        path = Path(settings.BASE_DIR) / dir_name
        path.mkdir(exist_ok=True)

@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "欢迎使用智能信息助手API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
