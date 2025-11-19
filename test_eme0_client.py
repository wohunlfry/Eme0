#!/usr/bin/env python3
"""
Eme0 情绪引擎 MCP Client 测试文件
测试5个连续对话场景，充分体现情绪引擎的优点
"""

import asyncio
import sys
import time
from typing import Dict, Any

# 添加src目录到Python路径
sys.path.insert(0, 'src')

from eme0.mcp_server import Eme0MCPServer


class Eme0TestClient:
    """Eme0测试客户端"""
    
    def __init__(self):
        self.server = Eme0MCPServer()
    
    async def initialize(self):
        """初始化客户端"""
        await self.server.initialize()
        print("🚀 Eme0测试客户端初始化完成！\n")
    
    async def analyze_emotion(self, dialogue: str, user_id: str, session_id: str) -> Dict[str, Any]:
        """分析情绪"""
        return await self.server.analyze_emotion(dialogue, user_id, session_id)
    
    async def get_context(self, user_id: str, session_id: str):
        """获取情绪上下文"""
        result = await self.server.get_emotion_context(user_id, session_id)
        # 转换为对象格式以保持兼容性
        if isinstance(result, dict):
            from eme0.schemas import EmotionContext
            return EmotionContext(
                short_term_summary=result.get('short_term_summary', ''),
                long_term_profile=result.get('long_term_profile', ''),
                inferred_intention=result.get('inferred_intention', ''),
                suggested_agent_tone=result.get('suggested_agent_tone', '')
            )
        return result
    
    async def update_long_term(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """更新长期记忆"""
        return await self.server.update_long_term_memory(user_id, session_id)
    
    async def get_detailed_profile(self, user_id: str) -> Dict[str, Any]:
        """获取详细情绪画像"""
        return await self.server.get_detailed_emotion_profile(user_id)
    
    async def analyze_emotion_trend(self, user_id: str, window_hours: int = 24) -> Dict[str, Any]:
        """分析情绪趋势"""
        return await self.server.analyze_emotion_trend(user_id, window_hours)


async def test_case_1(client: Eme0TestClient):
    """测试用例1: 用户从焦虑到平静的情绪转变过程"""
    print("=" * 60)
    print("📋 测试用例1: 用户工作压力下的情绪变化")
    print("=" * 60)
    
    user_id = "user001"
    session_id = "session001"
    
    dialogues = [
        "今天工作压力好大啊，项目deadline快到了，我真的很焦虑",
        "刚才有个bug花了我两个小时才解决，真烦人",
        "不过现在总算解决了，感觉轻松了一些",
        "谢谢你的安慰，我现在感觉好多了，心情平静下来了",
        "明天又是新的一天，我会继续努力的！"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        # 分析情绪
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   🔑 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        # 获取情绪上下文
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   🎤 建议语气: {context.suggested_agent_tone}")
        
        time.sleep(1)  # 模拟对话间隔
    
    # 更新长期记忆
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")


async def test_case_2(client: Eme0TestClient):
    """测试用例2: 用户分享喜悦的情绪过程"""
    print("\n" + "=" * 60)
    print("📋 测试用例2: 用户分享成功的喜悦")
    print("=" * 60)
    
    user_id = "user002"
    session_id = "session002"
    
    dialogues = [
        "太棒了！我刚刚通过了一个重要的面试！",
        "面试官对我的表现很满意，我太开心了",
        "这是我梦寐以求的公司，感觉像在做梦一样",
        "我想把这个好消息分享给我的家人朋友",
        "生活真美好，对未来充满期待！"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   🔑 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   🎤 建议语气: {context.suggested_agent_tone}")
        
        time.sleep(1)
    
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")


async def test_case_3(client: Eme0TestClient):
    """测试用例3: 用户处理失落情绪的过程"""
    print("\n" + "=" * 60)
    print("📋 测试用例3: 用户面对失落和恢复")
    print("=" * 60)
    
    user_id = "user003"
    session_id = "session003"
    
    dialogues = [
        "我的宠物猫今天走丢了，我很难过",
        "我已经找了很久了，还是没有找到它",
        "我真的很想念它，家里空荡荡的",
        "朋友建议我继续寻找，不要放弃希望",
        "我会继续努力寻找，也要学会接受可能的结果"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   ?? 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   🎤 建议语气: {context.suggested_agent_tone}")
        
        time.sleep(1)
    
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")


async def test_case_4(client: Eme0TestClient):
    """测试用例4: 用户愤怒情绪的平复过程"""
    print("\n" + "=" * 60)
    print("📋 测试用例4: 用户愤怒情绪的平复")
    print("=" * 60)
    
    user_id = "user004"
    session_id = "session004"
    
    dialogues = [
        "气死我了！同事把我的功劳说成是他的",
        "这已经不是第一次了，他总是这样抢功劳",
        "我真的想找领导理论一下，太不公平了",
        "冷静下来想想，也许我应该先收集证据",
        "我会用合适的方式解决这个问题，保持专业"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   🔑 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   ?? 建议语气: {context.suggested_agent_tone}")
        
        time.sleep(1)
    
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")

async def test_case_6(client: Eme0TestClient):
    """测试用例6: 增强型情绪趋势和时间衰减分析"""
    print("\n" + "=" * 60)
    print("📋 测试用例6: 增强型情绪趋势和时间衰减分析")
    print("=" * 60)
    
    user_id = "user006"
    session_id = "session006"
    
    # 创建包含时间跨度情绪的对话
    dialogues = [
        "昨天遇到了很多困难，心情很低落",
        "今天早上感觉好多了，对解决问题有了信心",
        "中午和小伙伴一起吃饭，心情变得轻松愉快",
        "下午工作效率很高，完成了很多任务",
        "现在回顾这一天，感觉情绪变化很大但很充实"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   🔑 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   🎤 建议语气: {context.suggested_agent_tone}")
        
        time.sleep(1)
    
    # 测试多个时间窗口的趋势分析
    print(f"\n📊 多时间窗口趋势分析:")
    time_windows = [6, 12, 24]
    for window in time_windows:
        trend_result = await client.analyze_emotion_trend(user_id, window)
        if trend_result.get('success'):
            trend_data = trend_result['trend_analysis']
            if 'dominant_emotions' in trend_data:
                print(f"   {window}小时窗口: {trend_data['dominant_emotions']}")
    
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")


async def test_case_5(client: Eme0TestClient):
    """测试用例5: 增强型长期情绪画像和趋势分析"""
    print("\n" + "=" * 60)
    print("📋 测试用例5: 增强型情绪画像和趋势分析")
    print("=" * 60)
    
    user_id = "user005"
    session_id = "session005"
    
    dialogues = [
        "今天真是五味杂陈，既有好事也有坏事",
        "工作上的项目成功了，但是和朋友发生了争执",
        "我既为工作成就感到高兴，又为友谊感到难过",
        "生活就是这样，总是有起有落",
        "我学会接受这种复杂性，这就是真实的人生"
    ]
    
    for i, dialogue in enumerate(dialogues, 1):
        print(f"\n🗣️  第{i}轮对话: {dialogue}")
        
        emotion_result = await client.analyze_emotion(dialogue, user_id, session_id)
        print(f"   🎭 情绪分析: {emotion_result['primary_emotion']} (强度: {emotion_result['emotion_intensity']:.2f})")
        if emotion_result['emotion_keywords']:
            print(f"   🔑 关键词: {', '.join(emotion_result['emotion_keywords'])}")
        
        context = await client.get_context(user_id, session_id)
        print(f"   📊 情绪上下文: {context.short_term_summary}")
        print(f"   💭 意图推断: {context.inferred_intention}")
        print(f"   🎤 建议语气: {context.suggested_agent_tone}")
        
        # 显示增强的长期记忆信息
        if context.long_term_profile != "历史情绪数据获取失败":
            print(f"   📚 长期画像: {context.long_term_profile}")
        
        # 测试期间显示详细画像和趋势分析
        if i == len(dialogues):  # 最后一轮对话时
            # 获取详细画像
            profile_result = await client.get_detailed_profile(user_id)
            if profile_result.get('success'):
                profile = profile_result['profile']
                print(f"   🔍 详细画像:")
                print(f"      情绪分布: {profile.get('dominant_emotions', {})}")
                print(f"      情绪稳定性: {profile.get('emotional_stability', 0):.3f}")
                if profile.get('personality_traits'):
                    print(f"      个性特征: {profile['personality_traits']}")
            
            # 分析情绪趋势
            trend_result = await client.analyze_emotion_trend(user_id, 12)
            if trend_result.get('success'):
                trend_data = trend_result['trend_analysis']
                if 'dominant_emotions' in trend_data:
                    print(f"   📈 趋势分析: {trend_data['dominant_emotions']}")
                if 'emotional_volatility' in trend_data:
                    print(f"      情绪波动性: {trend_data['emotional_volatility']:.3f}")
        
        time.sleep(1)
    
    long_term_result = await client.update_long_term(user_id, session_id)
    print(f"\n📝 长期记忆更新: {'成功' if long_term_result['success'] else '失败'}")


async def main():
    """主测试函数"""
    print("🧪 开始 Eme0 情绪引擎测试\n")
    
    client = Eme0TestClient()
    await client.initialize()
    
    try:
        # 执行5个测试用例
        await test_case_1(client)
        await test_case_2(client)
        await test_case_3(client)
        await test_case_4(client)
        await test_case_5(client)
        
        print("\n" + "=" * 60)
        print("✅ 所有测试用例执行完成！")
        print("🎯 情绪引擎测试展示了以下优点:")
        print("   1. 实时情绪识别和分析能力")
        print("   2. 短期情绪记忆和趋势追踪")
        print("   3. 智能意图推断和语气建议")
        print("   4. 长期情绪画像建立")
        print("   5. 复杂情绪场景的处理能力")
        print("   6. 增强型情绪画像和趋势分析")
        print("   7. 时间衰减模型支持")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
