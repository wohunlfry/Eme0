"""情绪推理模型实现"""
import logging
from typing import List

from .schemas import EmotionResult, EmotionContext
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class EmotionInferenceEngine:
    """Eme0 情感引擎主类"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def analyze_emotion(self, dialogue_turn: str, user_id: str, session_id: str = "") -> EmotionResult:
        """分析情绪"""
        logger.info(f"开始情绪分析: {user_id}/{session_id}")
        
        try:
            # 调用百度千帆API分析情绪
            emotion_result = await self.llm_client.analyze_emotion(dialogue_turn, user_id, session_id)
            
            logger.info(f"情绪分析完成: {emotion_result.primary_emotion}({emotion_result.emotion_intensity}))")
            
            return emotion_result
        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            return EmotionResult(
                primary_emotion="unknown",
                emotion_intensity=0.5,
                emotion_keywords=[],
                raw_llm_response=f"分析过程出错: {str(e)}"
            )