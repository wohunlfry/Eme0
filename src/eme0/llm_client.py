"""百度千帆LLM客户端实现"""
import asyncio
import aiohttp
import json
import logging

from .schemas import EmotionResult

logger = logging.getLogger(__name__)


class LLMClient:
    """百度千帆LLM客户端"""
    
    def __init__(self, config):
        self.config = config
    
    async def analyze_emotion(self, dialogue_turn: str, user_id: str, session_id: str = "") -> EmotionResult:
        """使用千帆大模型分析情绪"""
        if not self.config.api_key:
            logger.warning("千帆API密钥未配置，使用规则分析")
            return await self._fallback_rule_analysis(dialogue_turn)
        
        try:
            # 构造情绪分析prompt
            prompt = self._build_emotion_prompt(dialogue_turn)
            
            # 使用新的API格式 - 直接使用Bearer token认证
            url = "https://qianfan.baidubce.com/v2/chat/completions"
            
            payload = {
                "model": "ernie-4.5-turbo-128k",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "web_search": {
                    "enable": False,
                    "enable_citation": False,
                    "enable_trace": False
                },
                "plugin_options": {}
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
            # print(self.config.api_key)
            
            # 如果配置了appid，添加appid头
            if hasattr(self.config, 'appid') and self.config.appid:
                headers["appid"] = self.config.appid
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status == 200:
                        data = await response.json()
                        # 新API格式返回结果在choices字段中
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            if "message" in choice and "content" in choice["message"]:
                                result_text = choice["message"]["content"]
                                return self._parse_emotion_result(result_text)
                        
                        # 如果新格式解析失败，尝试旧格式
                        result_text = data.get("result", "")
                        return self._parse_emotion_result(result_text)
                    else:
                        error_text = await response.text()
                        logger.error(f"千帆API调用失败: {response.status} - {error_text}")
                        return await self._fallback_rule_analysis(dialogue_turn)
        
        except Exception as e:
            logger.error(f"千帆API调用异常: {e}")
            return await self._fallback_rule_analysis(dialogue_turn)
    
    def _build_emotion_prompt(self, dialogue: str) -> str:
        """构造情绪分析的prompt"""
        return f"""请分析以下对话中的情绪，并返回JSON格式的结果：

对话内容：{dialogue}

请返回以下格式的JSON：
{{
    "primary_emotion": "主要情绪（选择：happiness, sadness, anger, fear, surprise, neutral之一）",
    "emotion_intensity": 情绪强度（0.0-1.0之间的数值），
    "emotion_keywords": ["提取的情绪关键词1", "关键词2", "关键词3"],
    "analysis": "简短的情绪分析说明"
}}

请直接返回JSON，不要包含其他文字。"""
    
    def _parse_emotion_result(self, llm_response: str) -> EmotionResult:
        """解析LLM返回的情绪分析结果"""
        try:
            # 尝试解析JSON
            if "{" in llm_response and "}" in llm_response:
                start = llm_response.find("{")
                end = llm_response.rfind("}") + 1
                json_str = llm_response[start:end]
                data = json.loads(json_str)
                
                primary_emotion = data.get("primary_emotion", "neutral")
                emotion_intensity = float(data.get("emotion_intensity", 0.5))
                emotion_keywords = data.get("emotion_keywords", [])
                
                # 验证和标准化
                valid_emotions = ["happiness", "sadness", "anger", "fear", "surprise", "neutral"]
                if primary_emotion not in valid_emotions:
                    primary_emotion = "neutral"
                
                emotion_intensity = max(0.0, min(1.0, emotion_intensity))
                
                if not isinstance(emotion_keywords, list):
                    emotion_keywords = []
                
                return EmotionResult(
                    primary_emotion=primary_emotion,
                    emotion_intensity=emotion_intensity,
                    emotion_keywords=emotion_keywords,
                    raw_llm_response=llm_response
                )
            else:
                raise ValueError("响应不是有效的JSON格式")
        
        except Exception as e:
            logger.warning(f"解析LLM响应失败: {e}，使用规则分析")
            # 如果解析失败，使用规则分析
            return asyncio.create_task(self._fallback_rule_analysis(llm_response)).result()
    
    async def _fallback_rule_analysis(self, dialogue: str) -> EmotionResult:
        """备用规则分析"""
        text = dialogue.lower()
        
        # 基础情绪关键词检测
        emotion_keywords = {
            "happiness": ["开心", "高兴", "快乐", "愉快", "兴奋", "满足", "棒", "太好了", "哈哈", "嘻嘻"],
            "sadness": ["难过", "伤心", "失落", "沮丧", "不开心", "郁闷", "痛苦", "悲伤", "哭", "失望"],
            "anger": ["生气", "愤怒", "恼火", "讨厌", "烦", "气死", "该死", "混蛋", "可恶", "操"],
            "fear": ["害怕", "恐惧", "担心", "紧张", "焦虑", "不安", "恐慌", "忧虑", "怕", "慌"],
            "surprise": ["惊讶", "意外", "震惊", "奇怪", "没想到", "居然", "天啊", "哇", "竟然"]
        }
        
        primary_emotion = "neutral"
        emotion_intensity = 0.3
        detected_keywords = []
        
        # 检测情绪
        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    primary_emotion = emotion
                    emotion_intensity = min(0.8, emotion_intensity + 0.15)
                    detected_keywords.append(keyword)
        
        return EmotionResult(
            primary_emotion=primary_emotion,
            emotion_intensity=emotion_intensity,
            emotion_keywords=detected_keywords,
            raw_llm_response=f"规则分析结果: {primary_emotion}({emotion_intensity})"
        )