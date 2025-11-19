"""
Eme0 情绪引擎包
基于MCP Server标准的Agent情绪引擎
"""

__version__ = "0.1.0"

from .mcp_server import Eme0MCPServer
from .schemas import EmotionResult, EmotionContext, EmotionSummary
from .config import MemoryConfig
from .emotion_inference import EmotionInferenceEngine
from .memory_manager import MemoryManager
from .llm_client import LLMClient
from .config import load_config