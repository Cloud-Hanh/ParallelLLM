"""
Google Gemini Provider实现
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


class GoogleProvider(BaseProvider):
    """Google Gemini API提供商"""
    
    @property
    def provider_name(self) -> str:
        return "google"
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "gemini-pro",
            "gemini-pro-vision", 
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "text-embedding-004"  # embedding model
        ]
    
    @property
    def supports_chat(self) -> bool:
        return True
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    async def chat(self, params: RequestParams) -> APIResponse:
        """执行Google Gemini聊天请求"""
        self.active_requests += 1
        
        try:
            # 构建请求参数 - Gemini API格式
            contents = self._convert_messages_gemini(params.messages)
            
            request_params = {
                "contents": contents,
            }
            
            # 添加生成配置
            generation_config = {}
            if params.temperature is not None:
                generation_config["temperature"] = params.temperature
            if params.max_tokens is not None:
                generation_config["maxOutputTokens"] = params.max_tokens
            if params.top_p is not None:
                generation_config["topP"] = params.top_p
            if params.top_k is not None:
                generation_config["topK"] = params.top_k
            if params.stop is not None:
                generation_config["stopSequences"] = params.stop if isinstance(params.stop, list) else [params.stop]
            
            if generation_config:
                request_params["generationConfig"] = generation_config
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                }
                
                if self.config.headers:
                    headers.update(self.config.headers)
                
                # Google API使用query参数传递API key
                url = f"{self.config.api_base}/v1/models/{self.config.model}:generateContent?key={self.config.api_key}"
                
                async with session.post(
                    url,
                    headers=headers,
                    json=request_params,
                    timeout=None
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Google Gemini API failed: {response.status}, {error_text}"
                        )
                    
                    json_response = await response.json()
                    
                    # 解析响应
                    if "candidates" not in json_response or not json_response["candidates"]:
                        raise Exception("Empty response from Gemini API")
                    
                    content = json_response["candidates"][0]["content"]["parts"][0]["text"]
                    
                    # 解析使用统计
                    usage = None
                    if "usageMetadata" in json_response:
                        usage_data = json_response["usageMetadata"]
                        usage = Usage(
                            prompt_tokens=usage_data.get("promptTokenCount", 0),
                            completion_tokens=usage_data.get("candidatesTokenCount", 0),
                            total_tokens=usage_data.get("totalTokenCount", 0)
                        )
                    
                    return APIResponse(
                        content=content,
                        usage=usage,
                        raw_response=json_response
                    )
                    
        finally:
            self.active_requests -= 1
    
    async def embedding(self, params: EmbeddingParams) -> EmbeddingResponse:
        """执行Google embedding请求"""
        self.active_requests += 1
        
        try:
            request_params = {
                "model": f"models/{self.config.model}",
                "content": {
                    "parts": [{
                        "text": params.input_text
                    }]
                }
            }
            
            # 添加额外参数
            if params.extra_params:
                request_params.update(params.extra_params)
            
            # 执行API调用
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                }
                
                if self.config.headers:
                    headers.update(self.config.headers)
                
                url = f"{self.config.api_base}/v1/models/{self.config.model}:embedContent?key={self.config.api_key}"
                
                async with session.post(
                    url,
                    headers=headers,
                    json=request_params,
                    timeout=None
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(
                            f"Google Embedding API failed: {response.status}, {error_text}"
                        )
                    
                    json_response = await response.json()
                    
                    # 解析响应
                    embedding = json_response["embedding"]["values"]
                    
                    return EmbeddingResponse(
                        embedding=embedding,
                        usage=None,  # Google embedding API 不返回token使用信息
                        raw_response=json_response
                    )
                    
        finally:
            self.active_requests -= 1
    
    def _convert_messages_gemini(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """将消息转换为Gemini API格式"""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return contents