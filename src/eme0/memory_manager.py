"""情绪记忆管理模块"""
from typing import Dict, List, Optional, Any
from collections import deque
import time
import json
import logging
from datetime import datetime, timedelta

from .schemas import EmotionResult, EmotionSummary, EmotionProfile, DecayConfig

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期情绪记忆管理"""
    
    def __init__(self, max_length: int = 10):
        self.memories: Dict[str, Dict[str, deque]] = {}  # {user_id: {session_id: deque}}
        self.max_length = max_length
    
    def add_emotion_result(self, user_id: str, session_id: str, emotion_result: EmotionResult):
        """添加情绪分析结果"""
        key = f"{user_id}_{session_id}"
        
        if key not in self.memories:
            self.memories[key] = {}
        
        if session_id not in self.memories[key]:
            self.memories[key][session_id] = deque(maxlen=self.max_length)
        
        self.memories[key][session_id].append(emotion_result)
        logger.debug(f"已添加短期记忆: {user_id}/{session_id}")
    
    def get_recent_emotions(self, user_id: str, session_id: str) -> List[EmotionResult]:
        """获取最近的短期情绪记忆"""
        key = f"{user_id}_{session_id}"
        
        if key not in self.memories or session_id not in self.memories[key]:
            return []
        
        return list(self.memories[key][session_id])
    
    def clear_session(self, user_id: str, session_id: str):
        """清除指定会话的记忆"""
        key = f"{user_id}_{session_id}"
        
        if key in self.memories and session_id in self.memories[key]:
            del self.memories[key][session_id]
            # 如果用户的会话为空，则删除整个用户记录
            if not self.memories[key]:
                del self.memories[key]
    
    def generate_summary(self, user_id: str, session_id: str) -> EmotionSummary:
        """生成情绪总结"""
        recent_emotions = self.get_recent_emotions(user_id, session_id)
        
        if not recent_emotions:
            return EmotionSummary(
                user_id=user_id,
                session_id=session_id,
                dominant_emotion="unknown",
                emotion_trend="unknown",
                sensitive_topics=[],
                created_at=time.strftime("%Y-%m-%d %H:%M:%S")
            )
        
        # 计算主导情绪
        emotion_counts = {}
        for emotion in recent_emotions:
            if emotion.primary_emotion in emotion_counts:
                emotion_counts[emotion.primary_emotion] += 1
            else:
                emotion_counts[emotion.primary_emotion] = 1
        
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # 分析情绪趋势
        if len(recent_emotions) >= 2:
            first_intensity = recent_emotions[0].emotion_intensity
            last_intensity = recent_emotions[-1].emotion_intensity
        else:
            first_intensity = last_intensity = 0.5
        
        if last_intensity > first_intensity + 0.2:
            trend = "逐渐上升"
        elif last_intensity < first_intensity - 0.2:
            trend = "逐渐下降"
        else:
            trend = "相对稳定"
        
        # 收集敏感话题
        sensitive_topics = []
        for emotion in recent_emotions:
            sensitive_topics.extend(emotion.emotion_keywords)
        sensitive_topics = list(set(sensitive_topics))
        
        return EmotionSummary(
            user_id=user_id,
            session_id=session_id,
            dominant_emotion=dominant_emotion,
            emotion_trend=trend,
            sensitive_topics=sensitive_topics,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S")
        )


class LongTermMemory:
    """长期情绪记忆管理"""
    
    def __init__(self, storage_type: str = "memory", decay_config: Optional[DecayConfig] = None):
        self.storage_type = storage_type
        self.memories: Dict[str, List[EmotionSummary]] = {}  # {user_id: [EmotionSummary]}}
        self.profiles: Dict[str, EmotionProfile] = {}  # {user_id: EmotionProfile}
        self.decay_config = decay_config or DecayConfig()
        self.emotion_history: Dict[str, List[Dict[str, Any]]] = {}  # 详细情绪历史记录
    
    def store_summary(self, user_id: str, summary: EmotionSummary):
        """存储情绪总结（带时间衰减）"""
        if user_id not in self.memories:
            self.memories[user_id] = []
        
        # 应用时间衰减权重
        weighted_summary = self._apply_time_decay(user_id, summary)
        self.memories[user_id].append(weighted_summary)
        
        # 更新用户情绪画像
        self._update_emotion_profile(user_id, summary)
        
        logger.info(f"已存储长期记忆: {user_id}, 总结数: {len(self.memories[user_id])}")
    
    def _apply_time_decay(self, user_id: str, summary: EmotionSummary) -> EmotionSummary:
        """应用时间衰减权重"""
        if user_id not in self.memories:
            return summary
        
        # 计算时间衰减权重
        current_time = datetime.now()
        summaries = self.memories[user_id]
        
        if not summaries:
            return summary
        
        # 计算每个总结的时间权重（新数据权重更高）
        recent_summaries = []
        for s in summaries:
            # 计算时间差异（小时）
            try:
                summary_time = datetime.fromisoformat(s.created_at)
                hours_diff = (current_time - summary_time).total_seconds() / 3600
                # 计算衰减权重：随时间的增长而衰减
                weight = max(self.decay_config.min_weight, 
                           self.decay_config.decay_rate ** (hours_diff / self.decay_config.time_window_hours))
                
                # 创建带权重的总结副本
                weighted_summary = EmotionSummary(
                    user_id=s.user_id,
                    session_id=s.session_id,
                    dominant_emotion=s.dominant_emotion,
                    emotion_trend=s.emotion_trend,
                    sensitive_topics=s.sensitive_topics,
                    created_at=s.created_at,
                    duration_minutes=s.duration_minutes,
                    total_interactions=s.total_interactions
                )
                weighted_summary._weight = weight  # 添加权重属性
                recent_summaries.append(weighted_summary)
            except Exception as e:
                logger.warning(f"计算时间衰减权重失败: {e}")
                # 如果无法计算，使用默认权重
                s._weight = self.decay_config.min_weight
                recent_summaries.append(s)
        
        # 更新历史记录，只保留最近的数据
        self.memories[user_id] = recent_summaries[-self.decay_config.time_window_hours:]  # 保留最近的时间窗口内的数据
        
        return summary
    
    def _update_emotion_profile(self, user_id: str, summary: EmotionSummary):
        """更新用户情绪画像"""
        if user_id not in self.profiles:
            # 初始化用户画像
            self.profiles[user_id] = EmotionProfile(
                user_id=user_id,
                dominant_emotions={},
                emotion_trends={},
                emotional_stability=0.5,
                sensitive_topics=[],
                personality_traits={},
                last_updated=datetime.now().isoformat(),
                total_interactions=0
            )
        
        profile = self.profiles[user_id]
        
        # 更新主导情绪分布
        emotion = summary.dominant_emotion
        if emotion in profile.dominant_emotions:
            profile.dominant_emotions[emotion] += 1
        else:
            profile.dominant_emotions[emotion] = 1
        
        # 归一化情绪分布
        total = sum(profile.dominant_emotions.values())
        for e in profile.dominant_emotions:
            profile.dominant_emotions[e] = profile.dominant_emotions[e] / total
        
        # 更新情绪趋势
        trend_direction = self._parse_trend_direction(summary.emotion_trend)
        if emotion in profile.emotion_trends:
            profile.emotion_trends[emotion] += trend_direction
        else:
            profile.emotion_trends[emotion] = trend_direction
        
        # 归一化趋势强度
        max_trend = max(abs(t) for t in profile.emotion_trends.values()) if profile.emotion_trends else 1
        if max_trend > 0:
            for e in profile.emotion_trends:
                profile.emotion_trends[e] = profile.emotion_trends[e] / max_trend
        
        # 更新情绪稳定性（基于情绪变化频率）
        profile.emotional_stability = self._calculate_emotional_stability(user_id)
        
        # 更新敏感话题
        for topic in summary.sensitive_topics:
            if topic not in profile.sensitive_topics:
                profile.sensitive_topics.append(topic)
        
        # 更新个性特征（基于情绪模式）
        self._update_personality_traits(profile, summary)
        
        # 更新总交互次数
        profile.total_interactions += summary.total_interactions
        
        # 更新时间戳
        profile.last_updated = datetime.now().isoformat()
    
    def _parse_trend_direction(self, trend_str: str) -> float:
        """解析趋势方向"""
        trend_mapping = {
            "逐渐上升": 0.1,
            "快速上升": 0.2,
            "逐渐下降": -0.1,
            "快速下降": -0.2,
            "相对稳定": 0.0,
            "波动较大": 0.05
        }
        return trend_mapping.get(trend_str, 0.0)
    
    def _calculate_emotional_stability(self, user_id: str) -> float:
        """计算情绪稳定性分数"""
        if user_id not in self.memories or len(self.memories[user_id]) < 2:
            return 0.5
        
        summaries = self.memories[user_id]
        
        # 计算情绪变化的频率和幅度
        emotion_changes = 0
        for i in range(1, len(summaries)):
            if summaries[i].dominant_emotion != summaries[i-1].dominant_emotion:
                emotion_changes += 1
        
        # 稳定性得分：变化越少越稳定
        stability = 1.0 - (emotion_changes / len(summaries))
        return max(0.1, min(0.9, stability))
    
    def _update_personality_traits(self, profile: EmotionProfile, summary: EmotionSummary):
        """更新个性特征"""
        # 基于情绪模式推断个性特征
        traits = profile.personality_traits
        
        # 情绪稳定性关联谨慎程度
        if profile.emotional_stability > 0.7:
            traits["谨慎"] = traits.get("谨慎", 0.0) + 0.1
        else:
            traits["随性"] = traits.get("随性", 0.0) + 0.1
        
        # 积极情绪关联开朗程度
        if summary.dominant_emotion in ["happiness", "excitement"]:
            traits["开朗"] = traits.get("开朗", 0.0) + 0.1
        
        # 负面情绪关联敏感程度
        if summary.dominant_emotion in ["sadness", "anxiety", "anger"]:
            traits["敏感"] = traits.get("敏感", 0.0) + 0.05
        
        # 归一化个性特征
        max_trait = max(traits.values()) if traits else 1
        if max_trait > 0:
            for trait in traits:
                traits[trait] = min(1.0, traits[trait] / max_trait)
    
    def get_user_profile(self, user_id: str) -> str:
        """获取用户情绪画像（增强版）"""
        if user_id not in self.profiles:
            return "暂无历史情绪数据"
        
        profile = self.profiles[user_id]
        
        # 构建详细的情绪画像描述
        profile_parts = []
        
        # 主导情绪分布
        if profile.dominant_emotions:
            sorted_emotions = sorted(profile.dominant_emotions.items(), 
                                   key=lambda x: x[1], reverse=True)
            top_emotions = [f"{e}({p:.2f})" for e, p in sorted_emotions[:3]]
            profile_parts.append(f"主导情绪分布: {', '.join(top_emotions)}")
        
        # 情绪趋势
        if profile.emotion_trends:
            trends_desc = []
            for emotion, trend in profile.emotion_trends.items():
                if abs(trend) > 0.1:
                    direction = "上升" if trend > 0 else "下降"
                    trends_desc.append(f"{emotion}({abs(trend):.2f}{direction})")
            if trends_desc:
                profile_parts.append(f"情绪趋势: {', '.join(trends_desc)}")
        
        # 情绪稳定性
        stability_desc = "非常稳定" if profile.emotional_stability > 0.8 else \
                         "较为稳定" if profile.emotional_stability > 0.6 else \
                         "中等稳定" if profile.emotional_stability > 0.4 else "情绪波动较大"
        profile_parts.append(f"情绪稳定性: {stability_desc}({profile.emotional_stability:.2f})")
        
        # 敏感话题
        if profile.sensitive_topics:
            profile_parts.append(f"敏感话题: {', '.join(profile.sensitive_topics[:5])}")
        
        # 个性特征
        if profile.personality_traits:
            top_traits = sorted(profile.personality_traits.items(), 
                              key=lambda x: x[1], reverse=True)[:3]
            traits_desc = [f"{t}({s:.2f})" for t, s in top_traits]
            profile_parts.append(f"个性特征: {', '.join(traits_desc)}")
        
        # 交互统计
        profile_parts.append(f"总交互次数: {profile.total_interactions}")
        
        return "\n".join(profile_parts)
    
    def get_detailed_profile(self, user_id: str) -> Optional[EmotionProfile]:
        """获取详细的情绪画像数据"""
        return self.profiles.get(user_id)


class MemoryManager:
    """情绪记忆管理器（增强版）"""
    
    def __init__(self, max_stm_length: int = 10, decay_config: Optional[DecayConfig] = None):
        self.stm = ShortTermMemory(max_length=max_stm_length)
        self.ltm = LongTermMemory(decay_config=decay_config)
        self.decay_config = decay_config or DecayConfig()
    
    def analyze_and_store(self, dialogue_turn: str, user_id: str, session_id: str, emotion_result: EmotionResult):
        """分析并存储情绪"""
        self.stm.add_emotion_result(user_id, session_id, emotion_result)
    
    def get_short_term_history(self, user_id: str, session_id: str) -> List[EmotionResult]:
        """获取短期历史"""
        return self.stm.get_recent_emotions(user_id, session_id)
    
    def get_long_term_profile(self, user_id: str) -> str:
        """获取长期情绪画像"""
        return self.ltm.get_user_profile(user_id)
    
    def get_detailed_emotion_profile(self, user_id: str) -> Optional[EmotionProfile]:
        """获取详细的情绪画像数据"""
        return self.ltm.get_detailed_profile(user_id)
    
    def analyze_emotion_trend(self, user_id: str, window_hours: int = 24) -> Dict[str, Any]:
        """分析指定时间窗口内的情绪趋势"""
        if user_id not in self.ltm.memories:
            return {"error": "用户暂无情绪数据"}
        
        summaries = self.ltm.memories[user_id]
        current_time = datetime.now()
        
        # 过滤指定时间窗口内的数据
        recent_summaries = []
        for summary in summaries:
            try:
                summary_time = datetime.fromisoformat(summary.created_at)
                hours_diff = (current_time - summary_time).total_seconds() / 3600
                if hours_diff <= window_hours:
                    recent_summaries.append(summary)
            except:
                continue
        
        if not recent_summaries:
            return {"error": f"最近{window_hours}小时内无情绪数据"}
        
        # 分析趋势
        trend_analysis = {
            "time_window_hours": window_hours,
            "total_summaries": len(recent_summaries),
            "dominant_emotions": {},
            "trend_directions": {},
            "emotional_volatility": self._calculate_volatility(recent_summaries)
        }
        
        # 统计主导情绪
        for summary in recent_summaries:
            emotion = summary.dominant_emotion
            if emotion in trend_analysis["dominant_emotions"]:
                trend_analysis["dominant_emotions"][emotion] += 1
            else:
                trend_analysis["dominant_emotions"][emotion] = 1
        
        # 分析趋势方向
        if len(recent_summaries) >= 2:
            first_emotion = recent_summaries[0].dominant_emotion
            last_emotion = recent_summaries[-1].dominant_emotion
            trend_analysis["trend_directions"]["recent_change"] = f"从{first_emotion}到{last_emotion}"
        
        return trend_analysis
    
    def _calculate_volatility(self, summaries: List[EmotionSummary]) -> float:
        """计算情绪波动性"""
        if len(summaries) < 2:
            return 0.0
        
        volatility = 0.0
        emotion_changes = 0
        
        for i in range(1, len(summaries)):
            if summaries[i].dominant_emotion != summaries[i-1].dominant_emotion:
                emotion_changes += 1
        
        volatility = emotion_changes / len(summaries)
        return volatility
    
    def update_long_term_memory(self, user_id: str, summary: EmotionSummary):
        """更新长期记忆"""
        self.ltm.store_summary(user_id, summary)
    
    def clear_session(self, user_id: str, session_id: str):
        """清除会话记忆"""
        self.stm.clear_session(user_id, session_id)