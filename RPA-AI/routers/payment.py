from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
from pathlib import Path
from datetime import datetime
from ..payment.payment_processor import PaymentProcessor

router = APIRouter()
templates = Jinja2Templates(directory="templates")

class PaymentRequest(BaseModel):
    """支付请求模型"""
    items: List[Dict]
    user_info: Optional[Dict] = None
    scene_type: Optional[str] = None

class PaymentStatusRequest(BaseModel):
    """支付状态请求模型"""
    order_id: str

@router.post("/create")
async def create_payment(request: PaymentRequest):
    """创建支付订单"""
    try:
        processor = PaymentProcessor()
        
        # 分析支付场景
        scene_result = await processor.analyze_payment_scene(
            items=request.items,
            user_info=request.user_info,
            scene_type=request.scene_type
        )
        
        # 生成订单ID
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 生成支付数据
        pay_data = {
            "order_id": order_id,
            "price_info": scene_result["price_info"],
            "product_id": f"PROD_{datetime.now().timestamp()}"
        }
        
        # 生成支付二维码
        qrcode_url = processor.generate_qr_code(pay_data)
        
        # 保存订单信息
        order_file = Path(f"orders/{order_id}.json")
        order_file.parent.mkdir(exist_ok=True)
        with open(order_file, 'w', encoding='utf-8') as f:
            json.dump({
                "order_id": order_id,
                "items": request.items,
                "scene_result": scene_result,
                "pay_data": pay_data,
                "create_time": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
        return {
            "order_id": order_id,
            "scene_result": scene_result,
            "qrcode_url": qrcode_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pay/{order_id}", response_class=HTMLResponse)
async def show_payment(request: Request, order_id: str):
    """显示支付页面"""
    try:
        # 读取订单信息
        order_file = Path(f"orders/{order_id}.json")
        if not order_file.exists():
            raise HTTPException(status_code=404, detail="订单不存在")
            
        with open(order_file, 'r', encoding='utf-8') as f:
            order_data = json.load(f)
            
        # 检测设备类型
        user_agent = request.headers.get("user-agent", "").lower()
        is_mobile = "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent
        
        # 选择模板
        template = order_data["scene_result"]["template"]
        if not Path(template).exists():
            template = "payment_simple.html"
            
        return templates.TemplateResponse(
            template,
            {
                "request": request,
                "order_id": order_id,
                "items": order_data["items"],
                "price_info": order_data["scene_result"]["price_info"],
                "qrcode_url": order_data["pay_data"]["qrcode_url"],
                "is_mobile": is_mobile,
                "title": "微信支付",
                "description": "请使用微信扫码支付"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{order_id}")
async def check_payment_status(order_id: str):
    """检查支付状态"""
    try:
        processor = PaymentProcessor()
        result = await processor.verify_payment(order_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify")
async def payment_notify(request: Request):
    """支付回调通知处理"""
    try:
        # 获取通知数据
        data = await request.json()
        
        # 验证签名（实际项目中需要实现）
        
        # 更新订单状态
        order_id = data.get("order_id")
        if order_id:
            order_file = Path(f"orders/{order_id}.json")
            if order_file.exists():
                with open(order_file, 'r', encoding='utf-8') as f:
                    order_data = json.load(f)
                    
                order_data["status"] = "paid"
                order_data["paid_time"] = datetime.now().isoformat()
                order_data["payment_data"] = data
                
                with open(order_file, 'w', encoding='utf-8') as f:
                    json.dump(order_data, f, ensure_ascii=False, indent=2)
        
        return {"return_code": "SUCCESS"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
