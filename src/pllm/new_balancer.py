"""
重构后的负载均衡器，使用新的Provider架构
"""
from typing import Dict, List, Any, Optional
import time
import logging
import asyncio
import yaml
import random
from collections import deque

from .providers import (
    BaseProvider, 
    ProviderConfig, 
    ChatMessage, 
    RequestParams, 
    EmbeddingParams,
    get_provider_class
)


class LoadBalancer:
    """智能负载均衡器，管理多个LLM Provider"""
    
    def __init__(self, config_path: str):
        self.providers: Dict[str, List[BaseProvider]] = {}
        self.logger = logging.getLogger("pllm.balancer")
        self.load_config(config_path)
        self.start_health_check()
    
    def load_config(self, config_path: str) -> None:
        """加载并解析YAML配置文件，支持每个提供商有多个API密钥"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            # 初始化每个提供商的Provider实例
            llm_config = config.get("llm", {})
            if not llm_config:
                raise ValueError("Missing 'llm' section in config")
            
            providers_str = llm_config.get("use", "")
            if not providers_str:
                raise ValueError("No providers specified in config")
            
            self.active_providers = [p.strip() for p in providers_str.split(",")]
            self.providers = {}
            
            # 遍历所有支持的provider配置
            for provider_name in self.active_providers:
                provider_configs = llm_config.get(provider_name, [])
                if not provider_configs:
                    raise ValueError(f"No configuration found for provider: {provider_name}")
                
                # 支持单配置和多配置格式
                if isinstance(provider_configs, dict):
                    provider_configs = [provider_configs]
                
                # 获取Provider类并创建实例
                provider_class = get_provider_class(provider_name)
                provider_instances = []
                
                for config_dict in provider_configs:
                    # 创建ProviderConfig实例
                    provider_config = ProviderConfig(
                        api_key=config_dict["api_key"],
                        api_base=config_dict["api_base"],
                        model=config_dict["model"],
                        rate_limit=config_dict.get("rate_limit", 5),
                        quota=config_dict.get("quota"),
                        headers=config_dict.get("headers"),
                        extra_params=config_dict.get("extra_params")
                    )
                    
                    # 创建Provider实例
                    provider_instance = provider_class(provider_config)
                    provider_instances.append(provider_instance)
                
                self.providers[provider_name] = provider_instances
                self.logger.info(
                    f"Initialized {len(provider_instances)} providers for {provider_name}"
                )
        
        except Exception as e:
            self.logger.error(f"Config load failed: {str(e)}")
            raise
    
    def get_best_provider(self, provider_name: Optional[str] = None) -> BaseProvider:
        """获取最佳Provider，支持指定提供商"""
        candidates = []
        
        # 如果指定了提供商，只在该提供商的Provider中选择
        target_providers = [provider_name] if provider_name else self.active_providers
        
        for provider in target_providers:
            for provider_instance in self.providers.get(provider, []):
                if provider_instance.is_available():
                    # 评分标准（数值越大优先级越高）：
                    # 1. 活跃请求数最少
                    # 2. 错误计数最少
                    # 3. 速率限制余量最多
                    # 4. 最近使用时间最久远
                    score = (
                        -provider_instance.active_requests * 1000,  # 主要因素
                        -provider_instance.error_count * 100,
                        (provider_instance.config.rate_limit - len(provider_instance.request_queue)) * 10,
                        -provider_instance.last_used,  # 次要因素
                    )
                    candidates.append((score, provider_instance))
        
        if candidates:
            # 找到最高分
            max_score = max(candidates, key=lambda x: x[0])[0]
            # 收集所有达到最高分的Provider
            best_candidates = [
                provider for score, provider in candidates if score == max_score
            ]
            # 随机选择一个
            best_provider = random.choice(best_candidates)
            best_provider.active_requests += 1  # 预占请求槽位
            return best_provider
        
        raise Exception("No available LLM providers")
    
    async def execute_request(
        self,
        messages: List[Dict[str, str]],
        provider: Optional[str] = None,
        retry_policy: str = "fixed",
        **kwargs,
    ) -> str:
        """执行请求，支持指定提供商和重试策略"""
        max_retries = 3
        retries = 0
        last_error = None
        
        while True:
            provider_instance = None
            try:
                provider_instance = self.get_best_provider(provider)
                self.logger.debug(f"Selected provider: {provider_instance.provider_name}")
                
                # 检查Provider是否支持聊天
                if not provider_instance.supports_chat:
                    raise ValueError(f"Provider {provider_instance.provider_name} does not support chat")
                
                # 转换消息格式
                chat_messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
                
                # 构建请求参数
                request_params = RequestParams(
                    messages=chat_messages,
                    temperature=kwargs.get("temperature"),
                    max_tokens=kwargs.get("max_tokens"),
                    stream=kwargs.get("stream"),
                    stop=kwargs.get("stop"),
                    top_p=kwargs.get("top_p"),
                    top_k=kwargs.get("top_k"),
                    frequency_penalty=kwargs.get("frequency_penalty"),
                    presence_penalty=kwargs.get("presence_penalty"),
                    response_format=kwargs.get("response_format"),
                    tools=kwargs.get("tools"),
                    extra_params={k: v for k, v in kwargs.items() 
                                if k not in ["temperature", "max_tokens", "stream", "stop", 
                                           "top_p", "top_k", "frequency_penalty", "presence_penalty",
                                           "response_format", "tools"]}
                )
                
                # 执行API调用
                response = await provider_instance.chat(request_params)
                provider_instance.record_usage(response)
                
                return response.content
                
            except Exception as e:
                retries += 1
                last_error = e
                
                if provider_instance:
                    provider_instance.mark_error(e)
                
                if retry_policy == "fixed":
                    if retries >= max_retries:
                        self.logger.error(f"All retries failed (policy={retry_policy})")
                        raise Exception(f"Failed after {retries} retries: {str(e)}")
                    self.logger.warning(f"Retry {retries}/{max_retries}")
                
                elif retry_policy == "infinite":
                    self.logger.warning(
                        f"Retry {retries} (infinite mode), last error: {str(e)}"
                    )
                    await asyncio.sleep(1)
                
                elif retry_policy == "retry_once":
                    if retries >= 1:
                        self.logger.error(f"Single retry failed (policy={retry_policy})")
                        raise Exception(f"Failed after {retries} retries: {str(e)}")
                    self.logger.warning(f"Retry {retries}/1")
                
                else:
                    raise ValueError(f"Invalid retry policy: {retry_policy}")
    
    async def execute_embedding_request(
        self, 
        input_text: str, 
        retry_policy: str = "fixed", 
        provider: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """执行Embedding请求"""
        max_retries = 3
        retries = 0
        last_error = None
        
        while True:
            provider_instance = None
            try:
                provider_instance = self.get_best_provider(provider)
                self.logger.debug(f"Selected provider for embedding: {provider_instance.provider_name}")
                
                # 检查Provider是否支持embedding
                if not provider_instance.supports_embedding:
                    raise ValueError(f"Provider {provider_instance.provider_name} does not support embedding")
                
                # 构建请求参数
                embedding_params = EmbeddingParams(
                    input_text=input_text,
                    encoding_format=kwargs.get("encoding_format", "float"),
                    extra_params={k: v for k, v in kwargs.items() if k != "encoding_format"}
                )
                
                # 执行API调用
                response = await provider_instance.embedding(embedding_params)
                provider_instance.record_usage(response)
                
                return response.embedding
                
            except Exception as e:
                retries += 1
                last_error = e
                
                if provider_instance:
                    provider_instance.mark_error(e)
                
                if retry_policy == "fixed":
                    if retries >= max_retries:
                        self.logger.error(
                            f"All embedding retries failed (policy={retry_policy})"
                        )
                        raise Exception(
                            f"Embedding failed after {retries} retries: {str(e)}"
                        )
                    self.logger.warning(f"Embedding retry {retries}/{max_retries}")
                
                elif retry_policy == "infinite":
                    self.logger.warning(
                        f"Embedding retry {retries} (infinite mode), last error: {str(e)}"
                    )
                    await asyncio.sleep(1)
                
                elif retry_policy == "retry_once":
                    if retries >= 1:
                        self.logger.error(f"Single embedding retry failed (policy={retry_policy})")
                        raise Exception(f"Embedding failed after {retries} retries: {str(e)}")
                    self.logger.warning(f"Embedding retry {retries}/1")
                
                else:
                    raise ValueError(f"Invalid retry policy: {retry_policy}")
    
    def start_health_check(self) -> None:
        """启动定期健康检查任务"""
        
        async def check():
            while True:
                await asyncio.sleep(300)  # 每5分钟检查一次
                self.logger.debug("Running health check")
                for provider_instance in self._all_providers():
                    if not provider_instance.is_active:
                        provider_instance.reset_error_count()
                        self.logger.info(f"Reactivated provider: {provider_instance.provider_name}")
        
        # 检查是否有运行中的事件循环，如果没有则不启动健康检查
        try:
            asyncio.get_running_loop()
            asyncio.create_task(check())
            self.logger.debug("Health check task started")
        except RuntimeError:
            self.logger.debug(
                "No running event loop, health check will not start automatically"
            )
            # 存储协程以便稍后手动启动
            self._health_check_coro = check
    
    def _all_providers(self) -> List[BaseProvider]:
        """获取所有Provider实例"""
        for provider_instances in self.providers.values():
            for provider_instance in provider_instances:
                yield provider_instance
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有Provider的使用统计信息"""
        stats = {}
        for provider_name, provider_instances in self.providers.items():
            provider_stats = []
            for i, provider_instance in enumerate(provider_instances):
                provider_stats.append({
                    "id": i,
                    "active": provider_instance.is_active,
                    "error_count": provider_instance.error_count,
                    "total_requests": provider_instance.total_requests,
                    "total_tokens": provider_instance.total_tokens,
                    "model": provider_instance.config.model,
                    "supports_chat": provider_instance.supports_chat,
                    "supports_embedding": provider_instance.supports_embedding,
                })
            stats[provider_name] = provider_stats
        return stats