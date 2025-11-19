"""Eme0 情绪引擎配置模块"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class BaiduQianfanConfig:
    """百度千帆API配置"""
    api_key: Optional[str] = None
    appid: Optional[str] = None
    model_name: str = "ernie-4.5-turbo-128k"  # 更新为Java示例中的模型
    endpoint: str = "https://qianfan.baidubce.com/v2/chat/completions"  # 更新为新的API端点


@dataclass
class MemoryConfig:
    """记忆管理配置（增强版）"""
    stm_max_length: int = 10  # 短期记忆最大长度
    ltm_storage_type: str = "memory"  # 长期记忆存储类型：memory, vector_db
    vector_db_path: Optional[str] = None
    decay_rate: float = 0.95  # 情绪衰减率
    time_window_hours: int = 24  # 时间窗口（小时）
    min_weight: float = 0.1  # 最小权重
    trend_weight: float = 0.3  # 趋势权重


@dataclass
class Eme0Config:
    """Eme0 全局配置"""
    baidu_qianfan: BaiduQianfanConfig
    memory: MemoryConfig
    server_host: str = "127.0.0.1"
    server_port: int = 8000


def load_config() -> Eme0Config:
    """加载配置"""
    # 从环境变量读取配置
    api_key = os.getenv("BAIDU_QIANFAN_API_KEY")
    # 检查是否配置了真实的API密钥
    if not api_key:
        print("⚠️  未检测到百度千帆API密钥配置")
        print("📝 请按以下步骤配置真实的API密钥:")
        print("1. 登录百度智能云控制台: https://cloud.baidu.com/")
        print("2. 进入'千帆大模型平台'")
        print("3. 创建应用或使用现有应用")
        print("4. 获取API Key，直接用作Bearer Token")
        print("5. 设置环境变量:")
        print("   export BAIDU_QIANFAN_API_KEY='your_real_api_key'")
        print("   export EMOTION_DECAY_RATE='0.95'  # 情绪衰减率")
        print("   export TIME_WINDOW_HOURS='24'     # 时间窗口")
        print("   export MIN_WEIGHT='0.1'           # 最小权重")
        print("   export TREND_WEIGHT='0.3'          # 趋势权重")
        print("6. 或者创建 .env 文件并添加上述配置")
        print("7. 重启应用程序")
        print("\n🔄 当前将使用备用规则分析模式")
        
        # 使用None值，让系统知道没有配置密钥
        api_key = None
    elif api_key.startswith("APIKey-"):
        print("⚠️  检测到使用的是示例API密钥")
        print("📝 示例密钥无法正常调用API，建议配置真实密钥")
        print("🔄 当前将尝试使用示例密钥，但预期会失败并降级到规则分析")
        print("💡 如需正常使用API，请获取真实密钥后重新配置")
    
    # 从环境变量读取appid
    appid = os.getenv("BAIDU_QIANFAN_APPID")
    
    baidu_config = BaiduQianfanConfig(
        api_key=api_key,
        appid=appid,
        model_name=os.getenv("BAIDU_MODEL_NAME", "ernie-4.5-turbo-128k")
    )
    
    memory_config = MemoryConfig(
        stm_max_length=int(os.getenv("STM_MAX_LENGTH", "10")),
        decay_rate=float(os.getenv("EMOTION_DECAY_RATE", "0.95")),
        time_window_hours=int(os.getenv("TIME_WINDOW_HOURS", "24")),
        min_weight=float(os.getenv("MIN_WEIGHT", "0.1")),
        trend_weight=float(os.getenv("TREND_WEIGHT", "0.3"))
    )
    
    return Eme0Config(
        baidu_qianfan=baidu_config,
        memory=memory_config
    )