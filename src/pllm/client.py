import asyncio
import logging
from typing import Dict, List, Optional, Union, Any

import yaml

from .balancer import LoadBalancer


def _run_async(coro):
    """Helper function to run async code from sync context"""
    try:
        # If we're already in an event loop, we can't use asyncio.run()
        loop = asyncio.get_running_loop()
        # Create a new thread with a new event loop
        import concurrent.futures
        import threading
        
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
            
    except RuntimeError:
        # No event loop running, use asyncio.run()
        return asyncio.run(coro)


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
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("pllm")

        # 初始化负载均衡器
        self.balancer = LoadBalancer(config_path)
        self.logger.info(
            f"PLLM Client initialized with {len(list(self.balancer._all_providers()))} API providers"
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_policy: str = "fixed",
        provider: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        发送聊天请求到LLM服务

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "Hello"}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成token数
            retry_policy: 重试策略（infinite, fixed, retry_once）
            provider: 指定提供商（openai/siliconflow等），None表示自动选择
            **kwargs: 其他参数传递给底层API

        Returns:
            生成的文本内容
        """
        return await self.balancer.execute_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            retry_policy=retry_policy,
            provider=provider,
            **kwargs,
        )

    async def generate(self, prompt: str, retry_policy: str = "fixed", **kwargs) -> str:
        """
        简化的文本生成接口

        Args:
            prompt: 用户输入的提示词
            retry_policy: 重试策略
            **kwargs: 其他参数传递给chat方法

        Returns:
            生成的文本内容
        """
        messages = [{"role": "user", "content": prompt}]
        response = await self.balancer.execute_request(
            messages, retry_policy=retry_policy, **kwargs
        )
        return response

    execute = generate

    def invoke(self, prompt: str, retry_policy: str = "fixed", **kwargs) -> str:
        """
        调用LLM服务

        Args:
            prompt: 用户输入的提示词
            retry_policy: 重试策略
            **kwargs: 其他参数传递给chat方法
        """
        return asyncio.run(self.generate(prompt, retry_policy=retry_policy, **kwargs))
    
    def invoke_batch(self, prompts: List[str], retry_policy: str = "fixed", **kwargs) -> List[str]:
        # TODO: not safe when failure occurs
        """
        批量调用LLM服务

        Args:
            prompts: 用户输入的提示词列表
            retry_policy: 重试策略
            **kwargs: 其他参数传递给chat方法
        """
        async def runner():
            tasks = [self.generate(prompt, retry_policy=retry_policy, **kwargs) for prompt in prompts]
            results = await asyncio.gather(*tasks)
            return results
        return _run_async(runner())

    async def embedding(
        self,
        text: str,
        encoding_format: str = "float",
        retry_policy: str = "fixed",
        **kwargs,
    ) -> List[float]:
        """
        获取文本的embedding向量

        Args:
            text: 需要编码的文本
            encoding_format: 编码格式（默认float）
            retry_policy: 重试策略
            **kwargs: 其他API参数

        Returns:
            embedding向量列表
        """
        response = await self.balancer.execute_embedding_request(
            input_text=text,
            encoding_format=encoding_format,
            retry_policy=retry_policy,
            **kwargs,
        )
        return response

    def chat_sync(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        同步执行聊天请求

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "Hello"}]
            **kwargs: 透传至chat()方法参数（temperature/max_tokens等）

        Returns:
            生成的文本内容（同chat()方法）
        """
        return _run_async(self.chat(messages, **kwargs))

    def generate_sync(self, prompt: str, retry_policy: str = "fixed", **kwargs) -> str:
        """
        同步执行文本生成

        Args:
            prompt: 用户输入的提示文本
            retry_policy: 重试策略配置（infinite, fixed, retry_once）
            **kwargs: 透传至generate()方法参数

        Returns:
            生成的文本内容（同generate()方法）
        """
        return _run_async(self.generate(prompt, retry_policy=retry_policy, **kwargs))

    def embedding_sync(
        self, text: str, encoding_format: str = "float", **kwargs
    ) -> List[float]:
        """
        同步执行embedding请求

        Args:
            text: 需要编码的文本
            encoding_format: 编码格式（默认float）
            **kwargs: 透传至embedding()方法参数

        Returns:
            embedding向量列表
        """
        return _run_async(
            self.embedding(text, encoding_format=encoding_format, **kwargs)
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取所有Provider的使用统计信息"""
        return self.balancer.get_stats()
