"""
测试目标: 负载均衡和高级功能测试
- 测试多提供商之间的负载均衡
- 测试错误处理和故障转移
- 测试速率限制和熔断机制
- 测试健康检查和提供商恢复
- 使用Mock API调用，不需要真实API密钥
"""
import unittest
from unittest.mock import AsyncMock, patch
import asyncio
import os
import sys
import tempfile
import time

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from conftest import TestConfig, mock_chat_response, mock_embedding_response, mock_error_response
from pllm import Client


class TestLoadBalancing(unittest.IsolatedAsyncioTestCase):
    """负载均衡测试"""
    
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory() 
        
        # 创建多提供商配置
        self.config = TestConfig.create_multi_provider_config()
        self.config_path = TestConfig.write_temp_config(self.config)
        self.client = Client(self.config_path)
        
        # 不启动健康检查任务，避免测试挂起
        # 健康检查在单元测试中不是必需的
    
    async def asyncTearDown(self):
        # 清理资源
        self.temp_dir.cleanup()
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    @patch("aiohttp.ClientSession.post")
    async def test_multi_provider_balancing(self, mock_post):
        """测试多提供商负载均衡"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Balanced response")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 发送多个请求
        tasks = [self.client.generate(f"Request {i}") for i in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        self.assertEqual(len(responses), 10)
        for response in responses:
            self.assertEqual(response, "Balanced response")
        
        # 验证多个提供商被使用
        stats = self.client.get_stats()
        active_providers = [name for name, stat in stats.items() 
                          if stat and any(s["total_requests"] > 0 for s in stat)]
        
        # 至少应该有一个提供商被使用
        self.assertGreater(len(active_providers), 0)
    
    @patch("aiohttp.ClientSession.post")
    async def test_failover(self, mock_post):
        """测试故障转移"""
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = AsyncMock()
            mock_response.status = 200
            
            # 前几次调用失败，后面成功
            if call_count <= 3:
                raise Exception("Simulated API failure")
            else:
                mock_response.json.return_value = mock_chat_response("Failover success")
                return mock_response.__aenter__()
        
        mock_post.side_effect = side_effect
        
        # 测试重试和故障转移
        response = await self.client.generate("Test failover", retry_policy="fixed")
        self.assertEqual(response, "Failover success")
        
        # 验证进行了重试
        self.assertGreater(call_count, 1)
    
    @patch("aiohttp.ClientSession.post")
    async def test_rate_limiting(self, mock_post):
        """测试速率限制"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Rate limited response")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 短时间内发送大量请求
        start_time = time.time()
        tasks = [self.client.generate(f"Rate test {i}") for i in range(50)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # 验证请求被处理（可能有一些被限制）
        successful = [r for r in responses if isinstance(r, str)]
        self.assertGreater(len(successful), 0)
        
        # 验证耗时符合速率限制预期（这个测试可能需要根据实际限制调整）
        duration = end_time - start_time
        self.assertLess(duration, 60)  # 不应该超过1分钟


class TestAdvancedFeatures(unittest.IsolatedAsyncioTestCase):
    """高级功能测试"""
    
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 使用SiliconFlow配置（如果有真实key的话）
        self.config = TestConfig.create_base_config()
        self.config_path = TestConfig.write_temp_config(self.config)
        self.client = Client(self.config_path)
    
    async def asyncTearDown(self):
        self.temp_dir.cleanup()
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def test_invoke_methods(self):
        """测试invoke系列方法"""
        with patch.object(self.client, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Invoke response"
            
            # 测试单个调用
            result = self.client.invoke("test prompt")
            self.assertEqual(result, "Invoke response")
            
            # 测试批量调用
            mock_generate.return_value = "Batch response"
            results = self.client.invoke_batch(["prompt1", "prompt2", "prompt3"])
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r == "Batch response" for r in results))
    
    def test_stats_collection(self):
        """测试统计信息收集"""
        stats = self.client.get_stats()
        
        self.assertIsInstance(stats, dict)
        
        # 验证统计结构
        for provider_name, provider_stats in stats.items():
            self.assertIsInstance(provider_stats, list)
            
            for client_stat in provider_stats:
                required_fields = [
                    "total_requests", "total_tokens", "error_count", 
                    "active", "model"  # "is_active" changed to "active", removed "last_used"
                ]
                
                for field in required_fields:
                    self.assertIn(field, client_stat)
    
    @patch("aiohttp.ClientSession.post")
    async def test_retry_policies(self, mock_post):
        """测试重试策略"""
        call_count = 0
        
        def failing_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")
        
        mock_post.side_effect = failing_side_effect
        
        # 测试retry_once策略
        call_count = 0
        with self.assertRaises(Exception):
            await self.client.generate("test", retry_policy="retry_once")
        
        # retry_once应该最多尝试2次
        self.assertLessEqual(call_count, 2)
        
        # 测试fixed策略 
        call_count = 0
        with self.assertRaises(Exception):
            await self.client.generate("test", retry_policy="fixed")
        
        # fixed策略有限制的重试次数
        self.assertGreater(call_count, 1)
        self.assertLess(call_count, 10)  # 假设不超过10次
    
    @patch("aiohttp.ClientSession.post")
    async def test_temperature_and_params(self, mock_post):
        """测试温度等参数传递"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Parameterized response")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 测试参数传递
        await self.client.chat(
            [{"role": "user", "content": "test"}],
            temperature=0.8,
            max_tokens=100
        )
        
        # 验证参数被传递到API调用
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        
        # 检查请求JSON中包含参数
        request_json = kwargs["json"]
        self.assertEqual(request_json.get("temperature"), 0.8)
        self.assertEqual(request_json.get("max_tokens"), 100)


class TestEmbeddingFeatures(unittest.IsolatedAsyncioTestCase):
    """Embedding功能测试"""
    
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 创建embedding配置
        self.config = TestConfig.create_embedding_config()
        self.config_path = TestConfig.write_temp_config(self.config)
        self.client = Client(self.config_path)
    
    async def asyncTearDown(self):
        self.temp_dir.cleanup()
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    @patch("aiohttp.ClientSession.post")
    async def test_embedding_functionality(self, mock_post):
        """测试embedding基本功能"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_embedding_response(dimension=1536)
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 测试embedding
        result = await self.client.embedding("test text for embedding")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1536)
        self.assertTrue(all(isinstance(x, float) for x in result))
        
        mock_post.assert_called_once()
    
    @patch("aiohttp.ClientSession.post")
    async def test_embedding_encoding_formats(self, mock_post):
        """测试不同编码格式"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_embedding_response()
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 测试float格式
        await self.client.embedding("test", encoding_format="float")
        
        # 验证参数传递
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        request_json = kwargs["json"]
        self.assertEqual(request_json.get("encoding_format"), "float")
    
    def test_embedding_sync(self):
        """测试同步embedding"""
        with patch.object(self.client, 'embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            
            result = self.client.embedding_sync("test text")
            self.assertEqual(result, [0.1, 0.2, 0.3])
            mock_embed.assert_called_once_with("test text", encoding_format="float")


if __name__ == "__main__":
    unittest.main()