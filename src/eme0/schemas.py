"""Eme0 核心数据结构定义"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class EmotionResult(BaseModel):
    """实时情绪分析结果"""
    primary_emotion: str = Field(..., description="主要情绪：高兴, 愤怒, 悲伤, 惊讶, 恐惧, 平静")
    emotion_intensity: float = Field(..., ge=0.0, le=1.0, description="情绪强度 (0.0 - 1.0)")
    emotion_keywords: List[str] = Field(default_factory=list, description="提取出的情绪关键词")
    raw_llm_response: Optional[str] = Field(None, description="LLM分析的原始输出（用于调试）")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="分析时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_emotion": "sadness",
                "emotion_intensity": 0.85,
                "emotion_keywords": ["失落", "不顺利"],
                "raw_llm_response": "...",
                "timestamp": "2025-11-20T01:00:45"
            }
        }


class EmotionContext(BaseModel):
    """提供给LLM的上下文"""
    short_term_summary: str = Field(..., description="短期情绪总结")
    long_term_profile: str = Field(..., description="长期情绪画像")
    inferred_intention: str = Field(..., description="推断的当前意图")
    suggested_agent_tone: str = Field(..., description="建议的Agent回复语气")
    
    class Config:
        json_schema_extra = {
            "example": {
                "short_term_summary": "用户在过去3句话中，情绪从‘平静’逐渐转为‘轻微不满’。",
                "long_term_profile": "根据历史记录，用户近期情绪波动较大，尤其容易在讨论工作时表现出‘焦虑’。",
                "inferred_intention": "当前的不满可能源于对之前某个问题的未解决。",
                "suggested_agent_tone": "共情且温柔地"
            }
        }


class EmotionSummary(BaseModel):
    """情绪记忆总结"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    dominant_emotion: str = Field(..., description="主导情绪")
    emotion_trend: str = Field(..., description="情绪趋势")
    sensitive_topics: List[str] = Field(default_factory=list, description="敏感话题")
    created_at: str = Field(..., description="创建时间")
    duration_minutes: float = Field(default=0.0, description="会话持续时间（分钟）")
    total_interactions: int = Field(default=0, description="会话交互次数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "session_id": "session456",
                "dominant_emotion": "anxiety",
                "emotion_trend": "逐渐上升",
                "sensitive_topics": ["工作压力", "截止期限"],
                "created_at": "2025-11-18 23:24:00",
                "duration_minutes": 15.5,
                "total_interactions": 24
            }
        }


class EmotionProfile(BaseModel):
    """长期情绪画像"""
    user_id: str = Field(..., description="用户ID")
    dominant_emotions: Dict[str, float] = Field(..., description="情绪分布权重")
    emotion_trends: Dict[str, float] = Field(..., description="情绪趋势强度")
    emotional_stability: float = Field(..., description="情绪稳定性分数")
    sensitive_topics: List[str] = Field(default_factory=list, description="敏感话题集合")
    personality_traits: Dict[str, float] = Field(default_factory=dict, description="个性特征")
    last_updated: str = Field(..., description="最后更新时间")
    total_interactions: int = Field(default=0, description="总交互次数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "dominant_emotions": {"happiness": 0.6, "sadness": 0.2, "anxiety": 0.2},
                "emotion_trends": {"happiness": 0.1, "sadness": -0.05, "anxiety": 0.08},
                "emotional_stability": 0.75,
                "sensitive_topics": ["工作压力", "家庭问题"],
                "personality_traits": {"开朗": 0.8, "敏感": 0.6, "谨慎": 0.4},
                "last_updated": "2025-11-20T01:00:45",
                "total_interactions": 156
            }
        }


class DecayConfig(BaseModel):
    """情绪衰减配置"""
    decay_rate: float = Field(default=0.95, description="衰减率（0-1之间）")
    time_window_hours: int = Field(default=24, description="时间窗口（小时）")
    min_weight: float = Field(default=0.1, description="最小权重")
    trend_weight: float = Field(default=0.3, description="趋势权重")
    
    class Config:
        json_schema_extra = {
            "example": {
                "decay_rate": 0.95,
                "time_window_hours": 24,
                "min_weight": 0.1,
                "trend_weight": 0.3
            }
        }