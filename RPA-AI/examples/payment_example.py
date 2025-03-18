import asyncio
import json
from pathlib import Path
from payment.payment_processor import PaymentProcessor

async def main():
    # 创建支付处理器实例
    processor = PaymentProcessor()
    
    try:
        # 示例商品信息
        items = [
            {
                "name": "年度会员",
                "price": 365.00,
                "quantity": 1,
                "type": "membership"
            },
            {
                "name": "Python进阶课程",
                "price": 299.00,
                "quantity": 1,
                "type": "course"
            }
        ]
        
        # 用户信息
        user_info = {
            "is_new": True,
            "membership_level": "free",
            "device": "mobile"
        }
        
        # 分析支付场景
        scene_result = await processor.analyze_payment_scene(
            items=items,
            user_info=user_info,
            scene_type="package"
        )
        print("场景分析结果：", json.dumps(scene_result, indent=2, ensure_ascii=False))
        
        # 生成支付数据
        pay_data = {
            "order_id": "TEST_ORDER_001",
            "price_info": scene_result["price_info"],
            "product_id": "TEST_PROD_001"
        }
        
        # 生成支付二维码
        qrcode_url = processor.generate_qr_code(pay_data)
        print(f"\n支付二维码URL：{qrcode_url}")
        
        # 保存示例数据
        example_dir = Path("examples/data")
        example_dir.mkdir(exist_ok=True)
        
        with open(example_dir / "payment_example.json", 'w', encoding='utf-8') as f:
            json.dump({
                "items": items,
                "user_info": user_info,
                "scene_result": scene_result,
                "pay_data": pay_data,
                "qrcode_url": qrcode_url
            }, f, ensure_ascii=False, indent=2)
            
        print("\n示例数据已保存到：", example_dir / "payment_example.json")
        
    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
