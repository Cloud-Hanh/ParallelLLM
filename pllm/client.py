import asyncio
import logging
from typing import Dict, List, Optional, Union, Any

import yaml

from .balancer import LLMClient, LoadBalancer

class Client:
    """
    PLLM Client - 并行LLM调用客户端
    
    简单易用的LLM负载均衡客户端，自动选择最佳API密钥进行调用
    
    Args:
        config_path: 配置文件路径，YAML格式
        log_level: 日志级别，默认为INFO
    """
    
    def __init__(self, config_path: str, log_level: int = logging.INFO):
        # 配置日志
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("pllm")
        
        # 初始化负载均衡器
        self.balancer = LoadBalancer(config_path)
        self.logger.info(f"PLLM Client initialized with {len(list(self.balancer._all_clients()))} API clients")
    
    async def chat(self, 
                  messages: List[Dict[str, str]], 
                  temperature: Optional[float] = None,
                  max_tokens: Optional[int] = None,
                  **kwargs) -> Dict[str, Any]:
        """
        发送聊天请求到LLM服务
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "Hello"}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            **kwargs: 其他参数传递给底层API
            
        Returns:
            API响应的JSON对象
        """
        return await self.balancer.execute_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """
        简化的文本生成接口
        
        Args:
            prompt: 用户输入的提示词
            **kwargs: 其他参数传递给chat方法
            
        Returns:
            生成的文本内容
        """
        messages = [{"role": "user", "content": prompt}]
        response = await self.chat(messages, **kwargs)
        return response["choices"][0]["message"]["content"]
    
    def chat_sync(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """同步版本的chat方法，适用于非异步环境"""
        return asyncio.run(self.chat(messages, **kwargs))
    
    def generate_sync(self, prompt: str, **kwargs) -> str:
        """同步版本的generate方法，适用于非异步环境"""
        return asyncio.run(self.generate(prompt, **kwargs))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取所有客户端的使用统计信息"""
        stats = {}
        for provider, clients in self.balancer.clients.items():
            provider_stats = []
            for i, client in enumerate(clients):
                provider_stats.append({
                    "id": i,
                    "active": client.is_active,
                    "error_count": client.error_count,
                    "total_requests": client.total_requests,
                    "total_tokens": client.total_tokens
                })
            stats[provider] = provider_stats
        return stats 