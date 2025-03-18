from typing import Dict, List, Optional
import logging
from pathlib import Path
import json
import asyncio
from datetime import datetime
from ..auto_rpa.base_auto_rpa import AutoRPABot

logger = logging.getLogger("auto_rpa_service")

class AutoRPAService:
    """智能RPA服务类"""
    
    def __init__(self):
        self.bots = {}
        self.task_history = []
        
    async def create_rpa_task(
        self,
        url: str,
        html_content: str,
        cookies: List[Dict],
        task_goal: str,
        workflow: Optional[str] = None,
        site_name: Optional[str] = None
    ) -> Dict:
        """创建RPA任务
        
        Args:
            url: 目标URL
            html_content: 网页源码
            cookies: Cookie列表
            task_goal: 任务目标
            workflow: 可选的操作流程
            site_name: 站点名称，如果不提供则从URL生成
        """
        try:
            # 生成站点名称
            if not site_name:
                from urllib.parse import urlparse
                site_name = urlparse(url).netloc.replace('.', '_')
            
            # 创建或获取机器人实例
            if site_name not in self.bots:
                self.bots[site_name] = AutoRPABot(site_name=site_name)
            bot = self.bots[site_name]
            
            # 分析页面
            analysis = await bot.analyze_page(
                html_content=html_content,
                task_goal=task_goal,
                workflow=workflow
            )
            
            # 生成脚本
            script = await bot.generate_script()
            
            # 执行脚本
            result = await bot.execute_script(url=url, cookies=cookies)
            
            # 记录任务历史
            task_record = {
                "site_name": site_name,
                "url": url,
                "task_goal": task_goal,
                "workflow": workflow,
                "analysis": analysis,
                "script": script,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            self.task_history.append(task_record)
            
            # 保存任务记录
            self._save_task_record(task_record)
            
            return {
                "status": "success",
                "task_id": len(self.task_history),
                "analysis": analysis,
                "script": script,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"创建RPA任务失败: {str(e)}")
            raise
            
    def get_task_history(self, site_name: Optional[str] = None) -> List[Dict]:
        """获取任务历史记录
        
        Args:
            site_name: 可选的站点名称过滤
        """
        if site_name:
            return [task for task in self.task_history if task["site_name"] == site_name]
        return self.task_history
        
    def _save_task_record(self, task_record: Dict):
        """保存任务记录到文件"""
        try:
            # 创建记录目录
            record_dir = Path("task_records")
            record_dir.mkdir(exist_ok=True)
            
            # 保存记录文件
            site_name = task_record["site_name"]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            record_file = record_dir / f"{site_name}_{timestamp}.json"
            
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(task_record, f, ensure_ascii=False, indent=2)
                
            logger.info(f"任务记录已保存到: {record_file}")
            
        except Exception as e:
            logger.error(f"保存任务记录失败: {str(e)}")
            
    def close(self):
        """关闭所有机器人实例"""
        for bot in self.bots.values():
            try:
                bot.close()
            except Exception as e:
                logger.error(f"关闭机器人失败: {str(e)}")
        self.bots.clear()
