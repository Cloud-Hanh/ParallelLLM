"""
SiliconFlow Provider实现
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


class SiliconFlowProvider(BaseProvider):
    """SiliconFlow API提供商"""
    
    @property
    def provider_name(self) -> str:
        return "siliconflow"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "deepseek-ai/DeepSeek-V2.5",
            "deepseek-ai/DeepSeek-Coder-V2-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "Qwen/Qwen2.5-32B-Instruct", 
            "Qwen/Qwen2.5-14B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "BAAI/bge-large-zh-v1.5",  # embedding model
            "BAAI/bge-base-en-v1.5",   # embedding model
        ]
    
    @property
    def supports_chat(self) -> bool:
        return True
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行SiliconFlow聊天请求"""
        self.active_requests += 1
        
        try:
            # 构建请求参数
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
            if params.top_k is not None:
                request_params["top_k"] = params.top_k
            if params.frequency_penalty is not None:
                request_params["frequency_penalty"] = params.frequency_penalty
            if params.stop is not None:
                request_params["stop"] = params.stop
            if params.response_format is not None:
                request_params["response_format"] = params.response_format
            if params.tools is not None:
                request_params["tools"] = params.tools
            
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
                            f"SiliconFlow API failed: {response.status}, {error_text}"
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
    
    async def embedding(self, params: EmbeddingParams) -> EmbeddingResponse:
        """执行SiliconFlow embedding请求"""
        self.active_requests += 1
        
        try:
            # 构建请求参数
            request_params = {
                "model": self.config.model,
                "input": params.input_text,
                "encoding_format": params.encoding_format
            }
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 清理空值参数
            request_params = {k: v for k, v in request_params.items() if v is not None}
            
            # 执行API调用
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                }
                
                if self.config.headers:
                    headers.update(self.config.headers)
                
                # SiliconFlow的embedding接口可能是不同的路径
                embedding_url = self.config.api_base.replace("/chat/completions", "/embeddings")
                
                async with session.post(
                    embedding_url,
                    headers=headers,
                    json=request_params,
                    timeout=None
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"SiliconFlow Embedding API failed: {response.status}, {error_text}"
                        )
                    
                    json_response = await response.json()
                    
                    # 解析响应
                    embedding = json_response["data"][0]["embedding"]
                    usage = self._parse_usage(json_response)
                    
                    return EmbeddingResponse(
                        embedding=embedding,
                        usage=usage,
                        raw_response=json_response
                    )
                    
        finally:
            self.active_requests -= 1