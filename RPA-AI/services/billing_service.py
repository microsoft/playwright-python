from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import json
from pathlib import Path
from decimal import Decimal

class BillingService:
    """计费服务"""
    
    def __init__(self):
        self.logger = logging.getLogger("billing")
        self.rules = self._load_billing_rules()
        
    def _load_billing_rules(self) -> Dict:
        """加载计费规则"""
        rules_file = Path("config/billing_rules.json")
        if not rules_file.exists():
            raise FileNotFoundError("计费规则文件不存在")
            
        with open(rules_file, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def calculate_subscription_price(
        self,
        plan_id: str,
        user_info: Dict,
        referral_info: Optional[Dict] = None
    ) -> Dict:
        """计算订阅价格
        
        Args:
            plan_id: 套餐ID
            user_info: 用户信息
            referral_info: 推荐信息
        """
        try:
            # 获取基础价格
            plan_type = self._get_plan_type(plan_id)
            base_price = self.rules["subscription_plans"][plan_type][plan_id]["price"]
            
            # 计算会员折扣
            vip_discount = self._calculate_vip_discount(user_info)
            
            # 计算推荐折扣
            referral_discount = self._calculate_referral_discount(referral_info)
            
            # 应用折扣
            final_price = base_price * vip_discount * referral_discount
            
            return {
                "plan_id": plan_id,
                "base_price": base_price,
                "vip_discount": vip_discount,
                "referral_discount": referral_discount,
                "final_price": final_price,
                "savings": base_price - final_price
            }
            
        except Exception as e:
            self.logger.error(f"计算订阅价格失败: {str(e)}")
            raise
            
    def calculate_token_price(
        self,
        token_count: int,
        user_info: Dict
    ) -> Dict:
        """计算Token价格
        
        Args:
            token_count: Token数量
            user_info: 用户信息
        """
        try:
            # 获取基础费率
            base_rate = self.rules["token_pricing"]["base_rate"]
            
            # 计算批量折扣
            bulk_discount = self._calculate_bulk_discount(token_count)
            
            # 计算会员折扣
            vip_discount = self._calculate_vip_discount(user_info)
            
            # 计算总价
            base_price = token_count * base_rate
            final_price = base_price * bulk_discount * vip_discount
            
            return {
                "token_count": token_count,
                "base_price": base_price,
                "bulk_discount": bulk_discount,
                "vip_discount": vip_discount,
                "final_price": final_price,
                "savings": base_price - final_price
            }
            
        except Exception as e:
            self.logger.error(f"计算Token价格失败: {str(e)}")
            raise
            
    def calculate_time_based_price(
        self,
        minutes: int,
        user_info: Dict
    ) -> Dict:
        """计算按时计费价格
        
        Args:
            minutes: 使用时长（分钟）
            user_info: 用户信息
        """
        try:
            # 找到最合适的时间套餐
            best_plan = self._find_best_time_plan(minutes)
            
            # 计算会员折扣
            vip_discount = self._calculate_vip_discount(user_info)
            
            # 计算最终价格
            base_price = best_plan["price"]
            final_price = base_price * vip_discount
            
            return {
                "plan": best_plan["name"],
                "minutes": minutes,
                "base_price": base_price,
                "vip_discount": vip_discount,
                "final_price": final_price,
                "savings": base_price - final_price
            }
            
        except Exception as e:
            self.logger.error(f"计算时间价格失败: {str(e)}")
            raise
            
    def calculate_referral_commission(
        self,
        referrer_info: Dict,
        order_amount: Decimal
    ) -> Dict:
        """计算推荐佣金
        
        Args:
            referrer_info: 推荐人信息
            order_amount: 订单金额
        """
        try:
            # 获取推荐等级
            level = self._get_referral_level(referrer_info)
            if not level:
                return {"commission": 0}
                
            # 计算佣金
            commission_rate = self.rules["referral_program"]["levels"][level]["commission_rate"]
            commission = order_amount * Decimal(str(commission_rate))
            
            return {
                "level": level,
                "commission_rate": commission_rate,
                "commission": commission
            }
            
        except Exception as e:
            self.logger.error(f"计算推荐佣金失败: {str(e)}")
            raise
            
    def _get_plan_type(self, plan_id: str) -> str:
        """获取套餐类型"""
        for plan_type, plans in self.rules["subscription_plans"].items():
            if plan_id in plans:
                return plan_type
        raise ValueError(f"未知的套餐ID: {plan_id}")
        
    def _calculate_vip_discount(self, user_info: Dict) -> float:
        """计算会员折扣"""
        vip_level = user_info.get("vip_level")
        if not vip_level or vip_level not in self.rules["vip_levels"]:
            return 1.0
            
        return self.rules["vip_levels"][vip_level]["benefits"]["discount"]
        
    def _calculate_referral_discount(self, referral_info: Optional[Dict]) -> float:
        """计算推荐折扣"""
        if not referral_info:
            return 1.0
            
        referral_count = referral_info.get("referral_count", 0)
        for rule in self.rules["referral_program"]["referral_discounts"]:
            if referral_count >= rule["referrals"]:
                return rule["discount"]
                
        return 1.0
        
    def _calculate_bulk_discount(self, token_count: int) -> float:
        """计算批量折扣"""
        for rule in reversed(self.rules["token_pricing"]["bulk_discounts"]):
            if token_count >= rule["threshold"]:
                return rule["discount"]
                
        return 1.0
        
    def _find_best_time_plan(self, minutes: int) -> Dict:
        """查找最合适的时间套餐"""
        seconds = minutes * 60
        best_plan = None
        min_waste = float('inf')
        
        for plan_id, plan in self.rules["subscription_plans"]["time_based"].items():
            if plan["duration"] >= seconds:
                waste = plan["duration"] - seconds
                if waste < min_waste:
                    min_waste = waste
                    best_plan = {**plan, "id": plan_id}
                    
        if not best_plan:
            raise ValueError(f"未找到合适的时间套餐: {minutes}分钟")
            
        return best_plan
        
    def _get_referral_level(self, referrer_info: Dict) -> Optional[str]:
        """获取推荐等级"""
        referral_count = referrer_info.get("referral_count", 0)
        active_users = referrer_info.get("active_users", 0)
        
        for level, info in self.rules["referral_program"]["levels"].items():
            requirements = info["requirements"]
            if (referral_count >= requirements["min_referrals"] and
                active_users >= requirements["min_active_users"]):
                return level
                
        return None
