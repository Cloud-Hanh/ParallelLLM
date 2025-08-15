import asyncio
import logging
from typing import Dict, List, Optional, Union, Any

import yaml

from .balancer import LoadBalancer
from .validators import OutputValidator, ValidationResult


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
        output_validator: Optional[OutputValidator] = None,
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
            output_validator: 输出格式校验器，用于自动校验和重试
            **kwargs: 其他参数传递给底层API

        Returns:
            生成的文本内容
        """
        if output_validator is None:
            # 无格式校验，直接调用
            return await self.balancer.execute_request(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                retry_policy=retry_policy,
                provider=provider,
                **kwargs,
            )
        
        # 带格式校验的调用
        current_messages = messages.copy()
        attempts = 0
        
        while attempts <= output_validator.max_retries:
            try:
                response = await self.balancer.execute_request(
                    messages=current_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    retry_policy=retry_policy,
                    provider=provider,
                    **kwargs,
                )
                
                # 验证输出格式
                validation_result = output_validator.validate(response)
                
                if validation_result.is_valid:
                    self.logger.info(f"Output validation successful after {attempts + 1} attempts")
                    return response
                
                # 验证失败，准备重试
                attempts += 1
                if attempts <= output_validator.max_retries:
                    self.logger.warning(
                        f"Output validation failed (attempt {attempts}): {validation_result.error_message}"
                    )
                    
                    # 添加重试提示到消息中
                    retry_message = {
                        "role": "assistant", 
                        "content": response
                    }
                    retry_prompt = {
                        "role": "user",
                        "content": validation_result.retry_prompt
                    }
                    current_messages.append(retry_message)
                    current_messages.append(retry_prompt)
                else:
                    # 超过最大重试次数
                    self.logger.error(
                        f"Output validation failed after {output_validator.max_retries + 1} attempts. "
                        f"Final error: {validation_result.error_message}"
                    )
                    raise ValueError(
                        f"Output validation failed after {output_validator.max_retries + 1} attempts. "
                        f"Final response: {response}. Error: {validation_result.error_message}"
                    )
                
            except Exception as e:
                # 如果是网络或API错误，让负载均衡器处理重试
                if attempts == 0 or "validation" not in str(e).lower():
                    raise e
                
                attempts += 1
                if attempts > output_validator.max_retries:
                    raise e
        
        # 不应该到达这里
        raise RuntimeError("Unexpected error in output validation logic")

    async def generate(
        self, 
        prompt: str, 
        retry_policy: str = "fixed", 
        output_validator: Optional[OutputValidator] = None,
        **kwargs
    ) -> str:
        """
        简化的文本生成接口

        Args:
            prompt: 用户输入的提示词
            retry_policy: 重试策略
            output_validator: 输出格式校验器，用于自动校验和重试
            **kwargs: 其他参数传递给chat方法

        Returns:
            生成的文本内容
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(
            messages, 
            retry_policy=retry_policy, 
            output_validator=output_validator,
            **kwargs
        )

    execute = generate

    def invoke(
        self, 
        prompt: str, 
        retry_policy: str = "fixed", 
        output_validator: Optional[OutputValidator] = None,
        **kwargs
    ) -> str:
        """
        调用LLM服务

        Args:
            prompt: 用户输入的提示词
            retry_policy: 重试策略
            output_validator: 输出格式校验器，用于自动校验和重试
            **kwargs: 其他参数传递给chat方法
        """
        return _run_async(
            self.generate(
                prompt, 
                retry_policy=retry_policy, 
                output_validator=output_validator,
                **kwargs
            )
        )
    
    def invoke_batch(
        self, 
        prompts: List[str], 
        retry_policy: str = "fixed", 
        output_validator: Optional[OutputValidator] = None,
        **kwargs
    ) -> List[str]:
        # TODO: not safe when failure occurs
        """
        批量调用LLM服务

        Args:
            prompts: 用户输入的提示词列表
            retry_policy: 重试策略
            output_validator: 输出格式校验器，应用于所有prompts
            **kwargs: 其他参数传递给chat方法
        """
        async def runner():
            tasks = [
                self.generate(
                    prompt, 
                    retry_policy=retry_policy, 
                    output_validator=output_validator,
                    **kwargs
                ) 
                for prompt in prompts
            ]
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

    def chat_sync(
        self, 
        messages: List[Dict[str, str]], 
        output_validator: Optional[OutputValidator] = None,
        **kwargs
    ) -> str:
        """
        同步执行聊天请求

        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "Hello"}]
            output_validator: 输出格式校验器，用于自动校验和重试
            **kwargs: 透传至chat()方法参数（temperature/max_tokens等）

        Returns:
            生成的文本内容（同chat()方法）
        """
        return _run_async(self.chat(messages, output_validator=output_validator, **kwargs))

    def generate_sync(
        self, 
        prompt: str, 
        retry_policy: str = "fixed", 
        output_validator: Optional[OutputValidator] = None,
        **kwargs
    ) -> str:
        """
        同步执行文本生成

        Args:
            prompt: 用户输入的提示文本
            retry_policy: 重试策略配置（infinite, fixed, retry_once）
            output_validator: 输出格式校验器，用于自动校验和重试
            **kwargs: 透传至generate()方法参数

        Returns:
            生成的文本内容（同generate()方法）
        """
        return _run_async(
            self.generate(
                prompt, 
                retry_policy=retry_policy, 
                output_validator=output_validator,
                **kwargs
            )
        )

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
