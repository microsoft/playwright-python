# 智能信息助手开发指南

## 项目概述

本项目是一个基于FastAPI的智能信息助手API服务，集成了多个功能模块：

- AI对话服务
- 职位搜索服务（赶集网、BOSS直聘）
- 企业信息查询服务
- 招聘分析服务

## 技术栈

- Python 3.8+
- FastAPI
- Playwright
- Pydantic
- asyncio

## 项目结构

```
RPA-AI/
├── bots/                   # 爬虫实现
│   ├── base_job_bot.py    # 职位爬虫基类
│   ├── ganji_bot.py       # 赶集网爬虫
│   ├── boss_bot.py        # BOSS直聘爬虫
│   └── base_llm_bot.py    # LLM机器人基类
├── core/                   # 核心配置
│   ├── config.py          # 配置管理
│   └── logging_config.py  # 日志配置
├── routers/               # API路由
│   ├── ai_chat.py        # AI对话路由
│   └── job_search.py     # 职位搜索路由
├── services/             # 业务服务
│   ├── llm_service.py   # LLM服务
│   └── job_service.py   # 职位服务
├── cookies/             # Cookies存储
├── logs/               # 日志文件
├── history/           # 对话历史
└── main.py           # 应用入口
```

## 开发环境配置

1. 安装依赖：
```bash
pip install -r requirements.txt
playwright install
```

2. 环境变量配置：
创建 `.env` 文件：
```env
DEBUG=True
HOST=0.0.0.0
PORT=8000
SECRET_KEY=your-secret-key
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要接口

1. AI对话
```
POST /api/v1/chat
```

2. 职位搜索
```
POST /api/v1/jobs/search
GET /api/v1/jobs/detail/{platform}/{job_id}
GET /api/v1/jobs/company/{platform}/{company_id}/jobs
POST /api/v1/jobs/analyze
```

## 开发规范

1. 代码风格
- 使用 black 进行代码格式化
- 使用 pylint 进行代码检查
- 类型注解必须完整

2. 错误处理
- 所有可能的异常都要捕获并记录
- 使用自定义异常类
- 保持错误信息的一致性

3. 日志规范
- 使用统一的日志配置
- 按模块分类记录日志
- 错误日志必须包含完整的上下文信息

4. 测试规范
- 单元测试覆盖率要求 > 80%
- 集成测试覆盖所有API接口
- 性能测试关注响应时间

## 爬虫开发指南

1. 创建新的爬虫
```python
from bots.base_job_bot import BaseJobBot

class NewJobBot(BaseJobBot):
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="your_site", log_level=log_level)
        
    async def search_jobs(self, keyword: str, **kwargs):
        # 实现搜索逻辑
        pass
```

2. 注意事项
- 实现必要的异常处理
- 添加详细的日志
- 使用 `_wait_for_selector` 等辅助方法
- 统一数据格式

## 部署指南

1. 生产环境配置
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export DEBUG=False
export HOST=0.0.0.0
export PORT=8000

# 启动服务
uvicorn main:app --host $HOST --port $PORT --workers 4
```

2. Docker部署
```bash
# 构建镜像
docker build -t rpa-ai .

# 运行容器
docker run -d -p 8000:8000 rpa-ai
```

## 常见问题

1. Playwright相关
- 确保正确安装浏览器：`playwright install`
- 检查代理设置
- 注意内存使用

2. 性能优化
- 使用连接池
- 实现缓存机制
- 控制并发数量

3. 错误处理
- 检查日志文件
- 使用debug模式
- 查看浏览器截图

## 更新日志

### v1.0.0
- 实现基础框架
- 添加AI对话功能
- 集成赶集网和BOSS直聘爬虫

## 联系方式

- 项目维护者：[维护者姓名]
- 邮箱：[邮箱地址]
- 问题反馈：[Issue链接]
