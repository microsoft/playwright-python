import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from .config import settings

def setup_logging():
    """配置日志系统"""
    # 创建logs目录
    log_dir = settings.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 按服务类型分类的文件处理器
    services = ['ai_chat', 'job_search', 'company_info', 'recruitment']
    for service in services:
        logger = logging.getLogger(service)
        log_file = log_dir / f"{service}_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    # 错误日志单独存储
    error_log = log_dir / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
