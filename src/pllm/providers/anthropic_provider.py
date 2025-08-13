"""
Anthropic Claude Provider实现
"""
from typing import List, Dict, Any
import aiohttp
import json

from .base import (
    BaseProvider, 
    ProviderConfig, 
    RequestParams, 
    EmbeddingParams,
    APIResponse, 
    EmbeddingResponse, 
    Usage
)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API提供商"""
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
    
    @property
    def supports_chat(self) -> bool:
        return True
    
    @property
    def supports_embedding(self) -> bool:
        return False  # Anthropic不提供embedding服务
    
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行Anthropic聊天请求"""
        self.active_requests += 1
        
        try:
            # 构建请求参数 - Anthropic API格式
            messages = self._convert_messages_anthropic(params.messages)
            
            request_params = {
                "model": self.config.model,
                "max_tokens": params.max_tokens or 4096,
                "messages": messages,
            }
            
            # 添加可选参数
            if params.temperature is not None:
                request_params["temperature"] = params.temperature
            if params.top_p is not None:
                request_params["top_p"] = params.top_p
            if params.stop is not None:
                request_params["stop_sequences"] = params.stop if isinstance(params.stop, list) else [params.stop]
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.config.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                
                if self.config.headers:
                    headers.update(self.config.headers)
                
                async with session.post(
                    f"{self.config.api_base}/v1/messages",
                    headers=headers,
                    json=request_params,
                    timeout=None
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Anthropic API failed: {response.status}, {error_text}"
                        )
                    
                    json_response = await response.json()
                    
                    # 解析响应
                    content = json_response["content"][0]["text"]
                    usage = None
                    if "usage" in json_response:
                        usage_data = json_response["usage"]
                        usage = Usage(
                            prompt_tokens=usage_data.get("input_tokens", 0),
                            completion_tokens=usage_data.get("output_tokens", 0),
                            total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
                        )
                    
                    return APIResponse(
                        content=content,
                        usage=usage,
                        raw_response=json_response
                    )
                    
        finally:
            self.active_requests -= 1
    
    def _convert_messages_anthropic(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """将消息转换为Anthropic API格式"""
        converted = []
        for msg in messages:
            # Anthropic要求role为user或assistant
            role = msg["role"]
            if role == "system":
                # 系统消息需要特殊处理，可以在第一条user消息前添加
                continue
            converted.append({
                "role": role,
                "content": msg["content"]
            })
        return converted