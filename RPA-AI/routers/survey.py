from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
from pathlib import Path
from ..survey.survey_generator import SurveyGenerator

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class SurveyRequest(BaseModel):
    query: str
    user_info: Optional[Dict] = None

class SurveyResponse(BaseModel):
    answers: Dict

@router.post("/generate")
async def generate_survey(request: SurveyRequest):
    """生成问卷"""
    try:
        generator = SurveyGenerator()
        result = await generator.analyze_user_query(request.query)
        
        # 保存问题列表到会话
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/survey/{survey_id}", response_class=HTMLResponse)
async def show_survey(request: Request, survey_id: str):
    """显示问卷页面"""
    try:
        # 获取问卷数据
        survey_file = Path(f"surveys/{survey_id}.json")
        if not survey_file.exists():
            raise HTTPException(status_code=404, detail="问卷不存在")
            
        with open(survey_file, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
            
        # 检测设备类型
        user_agent = request.headers.get("user-agent", "").lower()
        is_mobile = "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent
        
        return templates.TemplateResponse(
            "survey_template.html",
            {
                "request": request,
                "questions": survey_data["questions"],
                "is_mobile": is_mobile
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit/{survey_id}")
async def submit_survey(survey_id: str, response: SurveyResponse):
    """提交问卷答案"""
    try:
        generator = SurveyGenerator()
        
        # 保存每个问题的答案
        for question_id, answer in response.answers.items():
            generator.save_response(question_id, answer)
            
        return {"status": "success", "message": "提交成功"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/next-question/{survey_id}/{question_id}")
async def get_next_question(survey_id: str, question_id: str, user_info: Optional[Dict] = None):
    """获取下一个问题的提示语"""
    try:
        generator = SurveyGenerator()
        
        # 获取问卷数据
        survey_file = Path(f"surveys/{survey_id}.json")
        with open(survey_file, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
            
        # 找到当前问题的索引
        current_index = next(
            (i for i, q in enumerate(survey_data["questions"]) if q["id"] == question_id),
            -1
        )
        
        if current_index == -1 or current_index >= len(survey_data["questions"]) - 1:
            return {"status": "completed"}
            
        # 获取下一个问题
        next_question = survey_data["questions"][current_index + 1]
        
        # 生成友好的提示语
        prompt = await generator.generate_question_prompt(next_question, user_info)
        
        return {
            "status": "success",
            "question": next_question,
            "prompt": prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
