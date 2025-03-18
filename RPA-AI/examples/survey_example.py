import asyncio
from pathlib import Path
import json
from survey.survey_generator import SurveyGenerator

async def main():
    # 创建问卷生成器实例
    generator = SurveyGenerator()
    
    try:
        # 示例用户问题
        user_query = """
        我们正在开发一个新的移动应用，需要了解用户对现有应用的使用体验和新功能需求。
        重点关注：
        1. 使用频率和场景
        2. 遇到的问题
        3. 期望的新功能
        """
        
        # 分析用户问题并生成问卷
        result = await generator.analyze_user_query(user_query)
        print("问卷分析结果：", json.dumps(result, indent=2, ensure_ascii=False))
        
        # 为每个问题生成友好的提示语
        for question in result["questions"]:
            prompt = await generator.generate_question_prompt(
                question,
                user_info={"is_new_user": True}
            )
            print(f"\n问题 {question['id']} 的提示语：")
            print(prompt)
        
        # 保存问卷数据
        survey_dir = Path("surveys")
        survey_dir.mkdir(exist_ok=True)
        
        survey_file = survey_dir / "example_survey.json"
        with open(survey_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"\n问卷数据已保存到：{survey_file}")
        
        # 模拟用户回答
        answers = {
            "q1": "每天使用",
            "q2": ["社交功能", "资讯浏览"],
            "q3": "希望增加个性化推荐"
        }
        
        # 保存用户回答
        for question_id, answer in answers.items():
            response = generator.save_response(
                question_id,
                answer,
                user_info={"device": "mobile"}
            )
            print(f"\n保存回答：{response}")
            
    except Exception as e:
        print(f"发生错误：{str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
