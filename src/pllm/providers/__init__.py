"""
Provider包的初始化文件
导出所有Provider类和相关数据结构
"""

from .base import (
    BaseProvider, 
    ProviderConfig, 
    ChatMessage, 
    RequestParams, 
    EmbeddingParams,
    APIResponse, 
    EmbeddingResponse, 
    Usage
)

# 导入所有具体的Provider实现
from .openai_provider import OpenAIProvider
from .siliconflow_provider import SiliconFlowProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .deepseek_provider import DeepSeekProvider
from .zhipu_provider import ZhipuProvider

# Provider注册表
PROVIDER_REGISTRY = {
    "openai": OpenAIProvider,
    "siliconflow": SiliconFlowProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "deepseek": DeepSeekProvider,
    "zhipu": ZhipuProvider,
}

def get_provider_class(provider_name: str) -> type:
    """根据名称获取Provider类"""
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_name}. Available providers: {list(PROVIDER_REGISTRY.keys())}")
    return PROVIDER_REGISTRY[provider_name]

__all__ = [
    # 基础类和数据结构
    "BaseProvider",
    "ProviderConfig", 
    "ChatMessage",
    "RequestParams",
    "EmbeddingParams", 
    "APIResponse",
    "EmbeddingResponse",
    "Usage",
    # Provider实现类
    "OpenAIProvider",
    "SiliconFlowProvider", 
    "AnthropicProvider",
    "GoogleProvider",
    "DeepSeekProvider",
    "ZhipuProvider",
    # 工具函数
    "PROVIDER_REGISTRY",
    "get_provider_class",
]