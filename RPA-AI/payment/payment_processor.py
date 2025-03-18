from typing import Dict, List, Optional
import logging
from datetime import datetime
import json
from pathlib import Path
import qrcode
import base64
from io import BytesIO
from ..base_llm_bot import BaseLLMBot

class PaymentProcessor(BaseLLMBot):
    """智能支付处理器"""
    
    def __init__(self, log_level=logging.INFO):
        super().__init__(site_name="payment", log_level=log_level)
        self.payment_config = self._load_payment_config()
        self.discount_rules = self._load_discount_rules()
        
    def _load_payment_config(self) -> Dict:
        """加载支付配置"""
        config_file = Path("config/payment_config.json")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "appid": "your_appid",
            "mch_id": "your_mch_id",
            "api_key": "your_api_key",
            "notify_url": "https://your.domain/payment/notify"
        }
        
    def _load_discount_rules(self) -> List[Dict]:
        """加载折扣规则"""
        rules_file = Path("config/discount_rules.json")
        if rules_file.exists():
            with open(rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return [
            {
                "type": "amount",
                "threshold": 100,
                "discount": 0.9,
                "description": "满100元9折"
            },
            {
                "type": "package",
                "items": ["年度会员", "课程包"],
                "discount": 0.85,
                "description": "套餐85折"
            }
        ]
        
    async def analyze_payment_scene(
        self,
        items: List[Dict],
        user_info: Optional[Dict] = None,
        scene_type: Optional[str] = None
    ) -> Dict:
        """分析支付场景并选择合适的展示样式"""
        try:
            # 准备场景分析提示
            context = f"""
作为支付体验专家，请分析以下支付场景并推荐最佳展示方案：

商品信息：
{json.dumps(items, indent=2, ensure_ascii=False)}

用户信息：
{json.dumps(user_info, indent=2, ensure_ascii=False) if user_info else '新用户'}

场景类型：{scene_type or '未指定'}

请提供：
1. 推荐的页面样式
2. 价格展示方式
3. 折扣方案
4. 营销建议
5. 文案建议
"""
            messages = [
                {"role": "system", "content": "你是一个支付体验专家，精通各类支付场景的优化。"},
                {"role": "user", "content": context}
            ]
            
            response = await self.chat(messages)
            analysis = response["choices"][0]["message"]["content"]
            
            # 计算价格和折扣
            price_info = self._calculate_price(items)
            
            return {
                "scene_analysis": analysis,
                "price_info": price_info,
                "template": self._select_template(analysis),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"分析支付场景失败: {str(e)}")
            raise
            
    def _calculate_price(self, items: List[Dict]) -> Dict:
        """计算价格和可用折扣"""
        try:
            # 计算原价
            original_price = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
            
            # 查找可用折扣
            available_discounts = []
            final_price = original_price
            
            for rule in self.discount_rules:
                if rule["type"] == "amount" and original_price >= rule["threshold"]:
                    final_price = min(final_price, original_price * rule["discount"])
                    available_discounts.append(rule["description"])
                elif rule["type"] == "package":
                    item_names = [item["name"] for item in items]
                    if all(required in item_names for required in rule["items"]):
                        final_price = min(final_price, original_price * rule["discount"])
                        available_discounts.append(rule["description"])
                        
            return {
                "original_price": original_price,
                "final_price": final_price,
                "discount_amount": original_price - final_price,
                "available_discounts": available_discounts
            }
            
        except Exception as e:
            self.logger.error(f"计算价格失败: {str(e)}")
            raise
            
    def _select_template(self, analysis: str) -> str:
        """根据场景分析选择合适的模板"""
        # 这里可以根据分析结果选择不同的模板
        templates = {
            "simple": "templates/payment_simple.html",
            "package": "templates/payment_package.html",
            "promotion": "templates/payment_promotion.html"
        }
        
        # 默认使用简单模板
        return templates.get("simple")
        
    def generate_qr_code(self, pay_data: Dict) -> str:
        """生成支付二维码"""
        try:
            # 生成支付URL（实际项目中需要调用微信支付API）
            pay_url = f"weixin://wxpay/bizpayurl?appid={self.payment_config['appid']}&mch_id={self.payment_config['mch_id']}&nonce_str={datetime.now().timestamp()}&product_id={pay_data.get('product_id')}&time_stamp={int(datetime.now().timestamp())}&sign=your_sign"
            
            # 创建二维码
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(pay_url)
            qr.make(fit=True)
            
            # 转换为图片
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 转换为base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            self.logger.error(f"生成二维码失败: {str(e)}")
            raise
            
    async def verify_payment(self, order_id: str) -> Dict:
        """验证支付状态"""
        try:
            # 实际项目中需要调用微信支付API查询订单状态
            # 这里仅作演示
            return {
                "order_id": order_id,
                "status": "success",
                "paid_amount": 100,
                "paid_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"验证支付失败: {str(e)}")
            raise
