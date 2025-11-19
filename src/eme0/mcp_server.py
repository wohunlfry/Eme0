"""Eme0 情绪引擎 MCP Server 实现"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from functools import wraps

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 使用绝对导入避免相对导入问题
from eme0.schemas import EmotionContext, EmotionProfile, DecayConfig
from eme0.emotion_inference import EmotionInferenceEngine
from eme0.memory_manager import MemoryManager
from eme0.config import load_config
from eme0.llm_client import LLMClient

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def log_tool_usage(func):
    """工具调用的日志装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        # 获取函数签名参数名
        import inspect
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # 构建参数映射
        log_args = {}
        for i, arg in enumerate(args):
            if i < len(param_names) and param_names[i] != 'self':
                param_name = param_names[i]
                # 对敏感信息进行脱敏处理
                if param_name == 'dialogue_turn' and isinstance(arg, str) and len(arg) > 50:
                    log_args[param_name] = f"{arg[:50]}... (总长度: {len(arg)})"
                else:
                    log_args[param_name] = arg
        
        # 添加关键字参数
        for k, v in kwargs.items():
            if k != 'self':
                if k == 'dialogue_turn' and isinstance(v, str) and len(v) > 50:
                    log_args[k] = f"{v[:50]}... (总长度: {len(v)})"
                else:
                    log_args[k] = v
        
        logger.info(f"🛠️ 工具调用开始 - {tool_name}: 输入参数={log_args}")
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录输出结果（简化处理敏感信息）
            if result and isinstance(result, dict):
                result_log = {k: v for k, v in result.items() if k != 'raw_llm_response'}
                logger.info(f"✅ 工具调用成功 - {tool_name}: 耗时={execution_time:.3f}s, 输出={result_log}")
            else:
                logger.info(f"✅ 工具调用成功 - {tool_name}: 耗时={execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 工具调用失败 - {tool_name}: 耗时={execution_time:.3f}s, 错误={str(e)}")
            raise
    
    return wrapper


class Eme0MCPServer:
    """Eme0 情绪引擎 MCP 服务器"""
    
    def __init__(self):
        self.emotion_engine: Optional[EmotionInferenceEngine] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.llm_client: Optional[LLMClient] = None
    
    async def initialize(self):
        """初始化服务器"""
        logger.info("正在初始化 Eme0 情绪引擎...")
        
        config = load_config()
        
        # 初始化LLM客户端
        self.llm_client = LLMClient(config.baidu_qianfan)
        
        # 初始化情绪引擎
        self.emotion_engine = EmotionInferenceEngine(self.llm_client)
        
        # 初始化记忆管理器（带衰减配置）
        decay_config = DecayConfig(
            decay_rate=config.memory.decay_rate,
            time_window_hours=config.memory.time_window_hours,
            min_weight=config.memory.min_weight,
            trend_weight=config.memory.trend_weight
        )
        self.memory_manager = MemoryManager(
            max_stm_length=config.memory.stm_max_length,
            decay_config=decay_config
        )
        
        logger.info("Eme0 情绪引擎初始化完成！")
    
    @log_tool_usage
    async def analyze_emotion(self, dialogue_turn: str, user_id: str, session_id: str = "") -> Dict[str, Any]:
        """实时情绪分析"""
        start_time = time.time()
        
        if not self.emotion_engine or not self.memory_manager:
            raise RuntimeError("服务器未初始化")
        
        try:
            logger.info(f"📊 开始情绪分析 - 用户={user_id}, 会话={session_id}, 对话长度={len(dialogue_turn)}")
            
            # 调用情绪分析引擎
            emotion_result = await self.emotion_engine.analyze_emotion(dialogue_turn, user_id, session_id)
            
            # 存储到短期记忆
            self.memory_manager.analyze_and_store(dialogue_turn, user_id, session_id, emotion_result)
            
            execution_time = time.time() - start_time
            logger.info(f"🎭 情绪分析完成 - 主要情绪={emotion_result.primary_emotion}, 强度={emotion_result.emotion_intensity:.2f}, 耗时={execution_time:.3f}s")
            
            return {
                "primary_emotion": emotion_result.primary_emotion,
                "emotion_intensity": emotion_result.emotion_intensity,
                "emotion_keywords": emotion_result.emotion_keywords,
                "raw_llm_response": emotion_result.raw_llm_response,
                "success": True
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 情绪分析失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return {
                "primary_emotion": "unknown",
                "emotion_intensity": 0.0,
                "emotion_keywords": [],
                "success": False,
                "error": str(e)
            }
    
    @log_tool_usage
    async def get_emotion_context(self, user_id: str, session_id: str = "") -> Dict[str, Any]:
        """获取情绪上下文（增强版）"""
        start_time = time.time()
        
        if not self.memory_manager:
            raise RuntimeError("服务器未初始化")
        
        try:
            logger.info(f"📝 获取情绪上下文 - 用户={user_id}, 会话={session_id}")
            
            # 获取短期历史
            short_term_history = self.memory_manager.get_short_term_history(user_id, session_id)
            logger.debug(f"📋 获取短期历史 - 记录数={len(short_term_history)}")
            
            # 生成短期摘要
            stm_summary = self.memory_manager.stm.generate_summary(user_id, session_id)
            
            # 获取增强的长期画像
            long_term_profile = self._get_enhanced_long_term_profile(user_id, short_term_history)
            
            # 基于历史和当前情绪进行意图推断
            inferred_intention = await self._infer_intention(user_id, session_id, short_term_history)
            
            # 建议回复语气
            suggested_tone = await self._suggest_agent_tone(short_term_history)
            
            execution_time = time.time() - start_time
            logger.info(f"🔍 情绪上下文生成完成 - 短期摘要={stm_summary.dominant_emotion}, 长期画像长度={len(long_term_profile)}, 耗时={execution_time:.3f}s")
            
            return {
                "short_term_summary": stm_summary.dominant_emotion,
                "long_term_profile": long_term_profile,
                "inferred_intention": inferred_intention,
                "suggested_agent_tone": suggested_tone,
                "success": True
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 获取情绪上下文失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return {
                "short_term_summary": "当前情绪数据获取失败",
                "long_term_profile": "历史情绪数据获取失败",
                "inferred_intention": "未知",
                "suggested_agent_tone": "中立",
                "success": False,
                "error": str(e)
            }
    
    @log_tool_usage
    async def update_long_term_memory(self, user_id: str, session_id: str = "") -> Dict[str, Any]:
        """更新长期情绪记忆（增强版）"""
        start_time = time.time()
        
        if not self.memory_manager:
            raise RuntimeError("服务器未初始化")
        
        try:
            logger.info(f"📊 更新长期记忆 - 用户={user_id}, 会话={session_id}")
            
            # 生成最终总结（带会话统计）
            short_term_history = self.memory_manager.get_short_term_history(user_id, session_id)
            summary = self.memory_manager.stm.generate_summary(user_id, session_id)
            
            # 添加会话统计信息
            summary.duration_minutes = len(short_term_history) * 0.5  # 估算会话时长
            summary.total_interactions = len(short_term_history)
            
            logger.debug(f"?? 生成记忆总结 - 主导情绪={summary.dominant_emotion}, 趋势={summary.emotion_trend}, 交互次数={summary.total_interactions}")
            
            # 存储到长期记忆（带时间衰减）
            self.memory_manager.update_long_term_memory(user_id, summary)
            
            # 清除该会话的短期记忆
            self.memory_manager.clear_session(user_id, session_id)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ 长期记忆更新完成 - 耗时={execution_time:.3f}s, 清除会话={session_id}, 新增交互={summary.total_interactions}")
            
            return {
                "success": True,
                "summary_model": {
                    "user_id": summary.user_id,
                    "session_id": summary.session_id,
                    "dominant_emotion": summary.dominant_emotion,
                    "emotion_trend": summary.emotion_trend,
                    "sensitive_topics": summary.sensitive_topics,
                    "created_at": summary.created_at,
                    "duration_minutes": summary.duration_minutes,
                    "total_interactions": summary.total_interactions
                }
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 更新长期记忆失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @log_tool_usage
    async def get_detailed_emotion_profile(self, user_id: str) -> Dict[str, Any]:
        """获取详细情绪画像数据"""
        start_time = time.time()
        
        if not self.memory_manager:
            raise RuntimeError("服务器未初始化")
        
        try:
            logger.info(f"📊 获取详细情绪画像 - 用户={user_id}")
            
            profile = self.memory_manager.get_detailed_emotion_profile(user_id)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ 详细情绪画像获取完成 - 耗时={execution_time:.3f}s")
            
            if profile:
                return {
                    "success": True,
                    "profile": profile.dict()
                }
            else:
                return {
                    "success": False,
                    "error": "用户画像不存在"
                }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 获取详细情绪画像失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @log_tool_usage
    async def analyze_emotion_trend(self, user_id: str, window_hours: int = 24) -> Dict[str, Any]:
        """分析情绪趋势"""
        start_time = time.time()
        
        if not self.memory_manager:
            raise RuntimeError("服务器未初始化")
        
        try:
            logger.info(f"📈 分析情绪趋势 - 用户={user_id}, 时间窗口={window_hours}小时")
            
            trend_analysis = self.memory_manager.analyze_emotion_trend(user_id, window_hours)
            
            execution_time = time.time() - start_time
            logger.info(f"✅ 情绪趋势分析完成 - 耗时={execution_time:.3f}s")
            
            return {
                "success": True,
                "trend_analysis": trend_analysis
            }
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 情绪趋势分析失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _infer_intention(self, user_id: str, session_id: str, history: list) -> str:
        """推断用户意图（增强版）"""
        start_time = time.time()
        
        try:
            logger.debug(f"🤔 开始意图推断 - 用户={user_id}, 历史记录数={len(history)}")
            
            if not history:
                logger.debug("📭 无历史记录，返回默认意图")
                return "未知意图"
            
            recent_emotion = history[-1] if history else None
            if recent_emotion:
                intention = "一般交流意图"
                emotion_intensity = recent_emotion.emotion_intensity
                
                # 基于情绪强度和类型推断意图
                if recent_emotion.primary_emotion in ["anger", "frustration"]:
                    if emotion_intensity > 0.7:
                        intention = "用户强烈不满，需要立即解决或安抚"
                    else:
                        intention = "用户可能对某件事感到不满或需要帮助解决"
                elif recent_emotion.primary_emotion in ["sadness", "anxiety"]:
                    if emotion_intensity > 0.8:
                        intention = "用户处于负面情绪状态，需要情感支持和理解"
                    else:
                        intention = "用户可能需要安慰或支持"
                elif recent_emotion.primary_emotion in ["happiness", "excitement"]:
                    intention = "用户分享积极体验或寻求认可"
                elif recent_emotion.primary_emotion == "surprise":
                    intention = "用户对某个信息感到意外或惊讶"
                elif recent_emotion.primary_emotion == "neutral":
                    # 结合历史上下文推断中立情绪的意图
                    if len(history) > 1:
                        prev_emotion = history[-2]
                        if prev_emotion.primary_emotion in ["anger", "sadness"]:
                            intention = "用户情绪趋于平静，可能正在消化先前的情感"
                        else:
                            intention = "用户处于稳定状态，进行常规交流"
                    else:
                        intention = "初次交流，处于信息收集阶段"
                
                execution_time = time.time() - start_time
                logger.debug(f"💡 意图推断完成 - 最终意图={intention}, 耗时={execution_time:.3f}s")
                return intention
            
            return "一般交流意图"
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 意图推断失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return "意图推断失败"
    def _get_enhanced_long_term_profile(self, user_id: str, short_term_history: list) -> str:
        """获取增强的长期情绪画像"""
        try:
            # 获取基础长期画像
            base_profile = self.memory_manager.get_long_term_profile(user_id)
            
            # 如果短期历史为空，直接返回基础画像
            if not short_term_history:
                return base_profile
            
            # 结合短期历史丰富长期画像描述
            recent_emotion = short_term_history[-1] if short_term_history else None
            if recent_emotion:
                enhanced_profile = base_profile + f"\n当前情绪状态: {recent_emotion.primary_emotion}(强度:{recent_emotion.emotion_intensity:.2f})"
                return enhanced_profile
            
            return base_profile
        except Exception as e:
            logger.error(f"获取增强长期画像失败: {e}")
            return "情绪画像获取失败"
    
    async def _suggest_agent_tone(self, history: list) -> str:
        """建议Agent回复语气（增强版）"""
        start_time = time.time()
        
        try:
            logger.debug(f"🎤 开始语气建议 - 历史记录数={len(history)}")
            
            if not history:
                logger.debug("📭 无历史记录，返回默认语气")
                return "中立地"
            
            recent_emotion = history[-1] if history else None
            if recent_emotion:
                emotion = recent_emotion.primary_emotion
                intensity = recent_emotion.emotion_intensity
                tone = "中立地"
                
                # 基于情绪类型和强度推荐语气
                if emotion == "anger":
                    if intensity > 0.8:
                        tone = "极度冷静，避免对抗，采取安抚性语言"
                    elif intensity > 0.6:
                        tone = "保持冷静，耐心解释，展现理解"
                    else:
                        tone = "温和地解释，展现同理心"
                elif emotion == "sadness":
                    if intensity > 0.8:
                        tone = "极度共情，温柔安慰，提供情感支持"
                    elif intensity > 0.6:
                        tone = "共情且温柔地，展现理解和支持"
                    else:
                        tone = "温和地安慰，鼓励表达"
                elif emotion == "anxiety":
                    if intensity > 0.7:
                        tone = "稳定地安抚，提供确定性信息"
                    else:
                        tone = "安全地引导，减少不确定性"
                elif emotion == "happiness":
                    if intensity > 0.8:
                        tone = "热情洋溢地分享喜悦"
                    elif intensity > 0.6:
                        tone = "积极热情地回应"
                    else:
                        tone = "愉快地回应"
                elif emotion == "surprise":
                    tone = "平复惊讶，提供清晰解释"
                elif emotion == "neutral":
                    # 根据历史趋势调整语气
                    if len(history) > 1:
                        prev_emotion = history[-2]
                        if prev_emotion.primary_emotion in ["anger", "sadness"]:
                            tone = "温和地引导，帮助维持平静状态"
                        else:
                            tone = "自然地交流"
                    else:
                        tone = "中立地"
                
                execution_time = time.time() - start_time
                logger.debug(f"🎯 语气建议完成 - 建议语气={tone}, 耗时={execution_time:.3f}s")
                return tone
            
            return "中立地"
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ 语气建议失败 - 耗时={execution_time:.3f}s, 错误={str(e)}")
            return "中立地"


# 创建全局服务器实例
eme0_server = Eme0MCPServer()


# MCP工具定义（增强版）
TOOLS = [
    Tool(
        name="eme0_analyze_emotion",
        description="实时情绪分析工具。对当前的对话回合进行情绪识别，并更新短期记忆（带时间戳）。",
        inputSchema={
            "type": "object",
            "properties": {
                "dialogue_turn": {"type": "string", "description": "对话文本内容"},
                "user_id": {"type": "string", "description": "用户唯一标识"},
                "session_id": {"type": "string", "description": "会话ID（可选）"}
            },
            "required": ["dialogue_turn", "user_id"]
        }
    ),
    Tool(
        name="eme0_get_emotion_context",
        description="获取情绪上下文工具。基于短/长期记忆和推理模型，生成当前最相关的情绪描述（包含时间衰减分析）。",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户唯一标识"},
                "session_id": {"type": "string", "description": "会话ID（可选）"}
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="eme0_update_long_term_memory",
        description="更新长期情绪记忆工具。将短期情绪总结归档到长期记忆（支持时间衰减和会话统计）。",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户唯一标识"},
                "session_id": {"type": "string", "description": "会话ID（可选）"}
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="eme0_get_detailed_profile",
        description="获取详细情绪画像工具。返回用户的详细情绪画像数据，包含情绪分布、趋势、稳定性等统计信息。",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户唯一标识"}
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="eme0_analyze_emotion_trend",
        description="分析情绪趋势工具。分析指定时间窗口内的情绪变化趋势和波动性。",
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户唯一标识"},
                "window_hours": {"type": "number", "description": "时间窗口（小时，默认24）"}
            },
            "required": ["user_id"]
        }
    )
]


# 创建MCP服务器
server = Server("eme0-emotion-engine")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """处理工具列表请求"""
    start_time = time.time()
    
    logger.info("🛠️ 处理工具列表请求")
    result = TOOLS
    execution_time = time.time() - start_time
    
    logger.info(f"📋 工具列表返回完成 - 工具数量={len(result)}, 耗时={execution_time:.3f}s")
    return result


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """处理工具调用请求"""
    start_time = time.time()
    
    try:
        logger.info(f"🔧 MCP工具调用开始 - 工具名={name}, 参数数量={len(arguments)}")
        logger.debug(f"📨 详细参数: {arguments}")
        
        result_content = None
        if name == "eme0_analyze_emotion":
            dialogue_turn = arguments.get("dialogue_turn", "")
            user_id = arguments.get("user_id", "")
            session_id = arguments.get("session_id", "")
            
            result = await eme0_server.analyze_emotion(dialogue_turn, user_id, session_id)
            result_content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        
        elif name == "eme0_get_emotion_context":
            user_id = arguments.get("user_id", "")
            session_id = arguments.get("session_id", "")
            
            result = await eme0_server.get_emotion_context(user_id, session_id)
            result_content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        
        elif name == "eme0_update_long_term_memory":
            user_id = arguments.get("user_id", "")
            session_id = arguments.get("session_id", "")
            
            result = await eme0_server.update_long_term_memory(user_id, session_id)
            result_content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        
        elif name == "eme0_get_detailed_profile":
            user_id = arguments.get("user_id", "")
            
            result = await eme0_server.get_detailed_emotion_profile(user_id)
            result_content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        
        elif name == "eme0_analyze_emotion_trend":
            user_id = arguments.get("user_id", "")
            window_hours = arguments.get("window_hours", 24)
            
            result = await eme0_server.analyze_emotion_trend(user_id, window_hours)
            result_content = [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        
        else:
            result_content = [TextContent(type="text", text=f"未知工具: {name}")]
        
        execution_time = time.time() - start_time
        logger.info(f"✅ MCP工具调用完成 - 工具名={name}, 耗时={execution_time:.3f}s")
        
        return result_content
    
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ MCP工具调用失败 - 工具名={name}, 耗时={execution_time:.3f}s, 错误={str(e)}")
        return [TextContent(type="text", text=f"工具调用失败: {str(e)}")]


async def main():
    """主函数 - 启动Eme0情绪引擎 MCP Server"""
    start_time = time.time()
    
    logger.info("🚀 开始启动 Eme0 情绪引擎 MCP Server")
    
    # 初始化服务器
    await eme0_server.initialize()
    
    init_time = time.time() - start_time
    logger.info(f"✅ Eme0 情绪引擎 MCP Server 已启动并准备就绪！初始化耗时={init_time:.3f}s")
    logger.info("⏳ 等待MCP客户端连接...")
    
    # 使用stdio服务器运行
    async with stdio_server() as (read_stream, write_stream):
        logger.info("?? 开始MCP协议通信")
        await server.run(
            read_stream,
            write_stream,
            initialization_options={}
        )
    
    total_time = time.time() - start_time
    logger.info(f"🛑 Eme0 情绪引擎 MCP Server 已停止，总运行时间={total_time:.3f}s")


if __name__ == "__main__":
    import json
    asyncio.run(main())


