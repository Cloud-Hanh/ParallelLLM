"""
DeepSeek Provider实现
"""
from typing import List, Dict, Any
import aiohttp

from .base import (
    BaseProvider, 
    ProviderConfig, 
    RequestParams, 
    EmbeddingParams,
    APIResponse, 
    EmbeddingResponse, 
    Usage
)


class DeepSeekProvider(BaseProvider):
    """DeepSeek API提供商"""
    
    @property
    def provider_name(self) -> str:
        return "deepseek"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "deepseek-chat",
            "deepseek-coder",
            "deepseek-reasoner",
        ]
    
    @property
    def supports_chat(self) -> bool:
        return True
    
    @property
    def supports_embedding(self) -> bool:
        return False  # DeepSeek目前不提供embedding服务
    
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行DeepSeek聊天请求"""
        self.active_requests += 1
        
        try:
            # 构建请求参数 - 兼容OpenAI格式
            request_params = {
                "model": self.config.model,
                "messages": self._convert_messages(params.messages),
                "stream": params.stream or False,
            }
            
            # 添加可选参数
            if params.temperature is not None:
                request_params["temperature"] = params.temperature
            if params.max_tokens is not None:
                request_params["max_tokens"] = params.max_tokens
            if params.top_p is not None:
                request_params["top_p"] = params.top_p
            if params.frequency_penalty is not None:
                request_params["frequency_penalty"] = params.frequency_penalty
            if params.presence_penalty is not None:
                request_params["presence_penalty"] = params.presence_penalty
            if params.stop is not None:
                request_params["stop"] = params.stop
            if params.response_format is not None:
                request_params["response_format"] = params.response_format
            
            # 清理空值参数
            request_params = {k: v for k, v in request_params.items() if v is not None}
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                }
                
                if self.config.headers:
                    headers.update(self.config.headers)
                
                async with session.post(
                    self.config.api_base,
                    headers=headers,
                    json=request_params,
                    timeout=None
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"DeepSeek API failed: {response.status}, {error_text}"
                        )
                    
                    json_response = await response.json()
                    
                    # 解析响应
                    content = json_response["choices"][0]["message"]["content"]
                    usage = self._parse_usage(json_response)
                    
                    return APIResponse(
                        content=content,
                        usage=usage,
                        raw_response=json_response
                    )
                    
        finally:
            self.active_requests -= 1