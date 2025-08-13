"""
基础Provider抽象类和相关数据结构
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import time
import logging
from collections import deque


@dataclass
class ProviderConfig:
    """Provider配置数据类"""
    api_key: str
    api_base: str
    model: str
    rate_limit: int = 5
    quota: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class ChatMessage:
    """聊天消息数据类"""
    role: str
    content: str


@dataclass
class RequestParams:
    """通用请求参数"""
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingParams:
    """Embedding请求参数"""
    input_text: str
    encoding_format: str = "float"
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class Usage:
    """API使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class APIResponse:
    """统一的API响应格式"""
    content: str
    usage: Optional[Usage] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class EmbeddingResponse:
    """Embedding响应格式"""
    embedding: List[float]
    usage: Optional[Usage] = None
    raw_response: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """所有LLM Provider的基类"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.last_used = 0
        self.error_count = 0
        self.is_active = True
        self.request_queue = deque(maxlen=config.rate_limit)
        self.total_tokens = 0
        self.total_requests = 0
        self.active_requests = 0
        self.logger = logging.getLogger(f"pllm.{self.provider_name}")
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供商名称"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """返回支持的模型列表"""
        pass
    
    @property
    @abstractmethod
    def supports_chat(self) -> bool:
        """是否支持聊天接口"""
        pass
    
    @property
    @abstractmethod
    def supports_embedding(self) -> bool:
        """是否支持embedding接口"""
        pass
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        if not self.is_active:
            return False
        
        # 检查速率限制
        now = time.time()
        if len(self.request_queue) >= self.config.rate_limit:
            oldest = self.request_queue[0]
            if now - oldest < 60:  # 1分钟窗口
                return False
        return True
    
    def record_usage(self, response: Union[APIResponse, EmbeddingResponse]) -> None:
        """记录API使用情况"""
        if response.usage:
            self.total_tokens += response.usage.total_tokens
        self.total_requests += 1
        
        # 额度预警逻辑
        if self.config.quota and self.total_tokens > self.config.quota * 0.8:
            self.logger.warning(
                f"API quota nearing limit for {self.provider_name}: "
                f"{self.total_tokens}/{self.config.quota}"
            )
        
        self.request_queue.append(time.time())
        self.last_used = time.time()
    
    def mark_error(self, error: Exception) -> None:
        """标记错误并更新客户端状态"""
        self.error_count += 1
        self.logger.error(f"API error with {self.provider_name}: {str(error)}")
        
        if self.error_count > 3:  # 连续3次错误后标记为不可用
            self.is_active = False
            self.logger.warning(
                f"Provider {self.provider_name} marked as inactive due to errors"
            )
    
    def reset_error_count(self) -> None:
        """重置错误计数（健康检查时调用）"""
        self.error_count = 0
        self.is_active = True
        self.logger.info(f"Provider {self.provider_name} reactivated")
    
    @abstractmethod
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行聊天请求"""
        pass
    
    async def embedding(self, params: EmbeddingParams) -> EmbeddingResponse:
        """执行embedding请求（默认不支持）"""
        raise NotImplementedError(f"{self.provider_name} does not support embedding")
    
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """将ChatMessage转换为API格式"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def _parse_usage(self, raw_response: Dict[str, Any]) -> Optional[Usage]:
        """解析使用统计信息"""
        usage_data = raw_response.get("usage", {})
        if not usage_data:
            return None
        
        return Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )