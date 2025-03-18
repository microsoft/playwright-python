import asyncio
import json
from pathlib import Path
from services.auto_rpa_service import AutoRPAService

async def main():
    # 创建RPA服务实例
    service = AutoRPAService()
    
    try:
        # 示例：自动登录并获取数据
        url = "https://example.com/login"
        
        # 读取HTML源码
        html_file = Path("example_login.html")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 读取Cookies
        cookies_file = Path("example_cookies.json")
        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
            
        # 定义任务目标和流程
        task_goal = """
        1. 使用已保存的cookies登录系统
        2. 导航到用户列表页面
        3. 获取所有用户的基本信息
        4. 将数据保存为CSV文件
        """
        
        workflow = """
        1. 验证cookies是否有效
        2. 点击"用户管理"菜单
        3. 等待用户列表加载
        4. 获取表格数据
        5. 处理分页
        6. 导出数据
        """
        
        # 创建RPA任务
        result = await service.create_rpa_task(
            url=url,
            html_content=html_content,
            cookies=cookies,
            task_goal=task_goal,
            workflow=workflow,
            site_name="example_site"
        )
        
        print("任务执行结果:", json.dumps(result, indent=2, ensure_ascii=False))
        
        # 获取任务历史
        history = service.get_task_history()
        print("任务历史:", json.dumps(history, indent=2, ensure_ascii=False))
        
    finally:
        # 关闭服务
        service.close()

if __name__ == "__main__":
    asyncio.run(main())
