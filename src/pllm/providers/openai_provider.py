"""
OpenAI Provider实现
"""
from typing import List, Dict, Any
import aiohttp
from openai import AsyncOpenAI

from .base import (
    BaseProvider, 
    ProviderConfig, 
    RequestParams, 
    EmbeddingParams,
    APIResponse, 
    EmbeddingResponse, 
    Usage
)


class OpenAIProvider(BaseProvider):
    """OpenAI API提供商"""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
            "text-embedding-3-large", "text-embedding-3-small", 
            "text-embedding-ada-002"
        ]
    
    @property
    def supports_chat(self) -> bool:
        return True
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行OpenAI聊天请求"""
        self.active_requests += 1
        
        try:
            client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            
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
            if params.frequency_penalty is not None:
                request_params["frequency_penalty"] = params.frequency_penalty
            if params.presence_penalty is not None:
                request_params["presence_penalty"] = params.presence_penalty
            if params.stop is not None:
                request_params["stop"] = params.stop
            if params.response_format is not None:
                request_params["response_format"] = params.response_format
            if params.tools is not None:
                request_params["tools"] = params.tools
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            response = await client.chat.completions.create(**request_params)
            
            # 解析响应
            content = response.choices[0].message.content
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = Usage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            
            return APIResponse(
                content=content,
                usage=usage,
                raw_response=response.model_dump()
            )
            
        finally:
            self.active_requests -= 1
    
    async def embedding(self, params: EmbeddingParams) -> EmbeddingResponse:
        """执行OpenAI embedding请求"""
        self.active_requests += 1
        
        try:
            client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base
            )
            
            # 构建请求参数
            request_params = {
                "model": self.config.model,
                "input": params.input_text,
                "encoding_format": params.encoding_format
            }
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            response = await client.embeddings.create(**request_params)
            
            # 解析响应
            embedding = response.data[0].embedding
            usage = None
            if hasattr(response, 'usage') and response.usage:
                usage = Usage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=0,  # embedding没有completion tokens
                    total_tokens=response.usage.total_tokens
                )
            
            return EmbeddingResponse(
                embedding=embedding,
                usage=usage,
                raw_response=response.model_dump()
            )
            
        finally:
            self.active_requests -= 1