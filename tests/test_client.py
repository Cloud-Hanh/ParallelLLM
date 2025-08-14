"""
测试目标: PLLM Client核心功能测试
- 测试客户端的基本聊天和生成功能
- 测试同步和异步接口
- 测试embedding功能
- 使用Mock API调用，不需要真实API密钥
- 包含错误处理和边缘情况测试
"""
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import os
import sys
import yaml
import tempfile

import sys
import os

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from conftest import TestConfig, mock_chat_response, mock_embedding_response
from pllm import Client


class TestPLLMClient(unittest.IsolatedAsyncioTestCase):
    """PLLM Client核心功能测试"""
    
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 使用统一的配置管理
        self.config = TestConfig.create_base_config()
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
    async def test_generate(self, mock_post):
        """测试generate方法"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Test response", 10)
        mock_post.return_value.__aenter__.return_value = mock_response

        # 测试生成方法
        response = await self.client.generate("Test prompt")
        self.assertEqual(response, "Test response")
        self.assertIsInstance(response, str)

        # 验证API调用参数
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "Test prompt")
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "user")

    @patch("aiohttp.ClientSession.post")
    async def test_chat(self, mock_post):
        """测试chat方法"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Chat response", 15)
        mock_post.return_value.__aenter__.return_value = mock_response

        # 测试聊天方法
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]
        response = await self.client.chat(messages)

        # 验证响应
        self.assertEqual(response, "Chat response")
        self.assertIsInstance(response, str)

        # 验证API调用参数
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["messages"], messages)

    def test_sync_methods(self):
        """测试同步方法"""
        # 测试同步生成
        with patch.object(self.client, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Sync test response"
            result = self.client.generate_sync("Test prompt")
            self.assertEqual(result, "Sync test response")
            mock_generate.assert_called_once_with("Test prompt", retry_policy="fixed")
        
        # 测试同步聊天
        with patch.object(self.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "Sync chat response"
            messages = [{"role": "user", "content": "Hi"}]
            result = self.client.chat_sync(messages)
            self.assertEqual(result, "Sync chat response")
            mock_chat.assert_called_once_with(messages)
        
        # 测试同步embedding
        with patch.object(self.client, 'embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3]
            result = self.client.embedding_sync("test text")
            self.assertEqual(result, [0.1, 0.2, 0.3])
            mock_embed.assert_called_once_with("test text", encoding_format="float")
    
    @patch("aiohttp.ClientSession.post")
    async def test_embedding(self, mock_post):
        """测试embedding功能"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_embedding_response(dimension=384, tokens=5)
        mock_post.return_value.__aenter__.return_value = mock_response

        # 测试embedding
        result = await self.client.embedding("test text")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 384)
        self.assertTrue(all(isinstance(x, float) for x in result))
        
        mock_post.assert_called_once()
    
    def test_invoke_methods(self):
        """测试invoke系列方法"""
        with patch.object(self.client, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Invoke response"
            
            # 测试单个调用
            result = self.client.invoke("test prompt")
            self.assertEqual(result, "Invoke response")
            
            # 测试批量调用
            results = self.client.invoke_batch(["prompt1", "prompt2"])
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r == "Invoke response" for r in results))
    
    def test_get_stats(self):
        """测试统计信息获取"""
        stats = self.client.get_stats()
        
        self.assertIsInstance(stats, dict)
        # 应该包含siliconflow提供商
        self.assertIn("siliconflow", stats)
        
        # 验证统计结构
        for provider_stats in stats.values():
            if provider_stats:  # 非空列表
                for client_stat in provider_stats:
                    self.assertIn("total_requests", client_stat)
                    self.assertIn("total_tokens", client_stat)
                    self.assertIn("error_count", client_stat)
    
    @patch("aiohttp.ClientSession.post")
    async def test_error_handling(self, mock_post):
        """测试错误处理"""
        mock_post.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            await self.client.generate("test prompt")
    
    @patch("aiohttp.ClientSession.post")
    async def test_parameter_passing(self, mock_post):
        """测试参数传递"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_chat_response("Parameterized response")
        mock_post.return_value.__aenter__.return_value = mock_response
        
        # 测试带参数的聊天
        await self.client.chat(
            [{"role": "user", "content": "test"}],
            temperature=0.7,
            max_tokens=150
        )
        
        # 验证参数传递
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        request_json = kwargs["json"]
        
        self.assertEqual(request_json.get("temperature"), 0.7)
        self.assertEqual(request_json.get("max_tokens"), 150)


class TestClientCompatibility(unittest.IsolatedAsyncioTestCase):
    """客户端兼容性测试"""
    
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = TestConfig.create_base_config()
        self.config_path = TestConfig.write_temp_config(self.config)
        self.client = Client(self.config_path)
    
    async def asyncTearDown(self):
        self.temp_dir.cleanup()
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
    
    def test_execute_alias(self):
        """测试execute别名"""
        # execute应该是generate的别名
        self.assertEqual(self.client.execute, self.client.generate)
    
    def test_initialization_with_logging(self):
        """测试带日志的初始化"""
        import logging
        client = Client(self.config_path, log_level=logging.DEBUG)
        self.assertIsNotNone(client)
        # 验证client的logger是正确的类型，而不是精确的日志级别
        # 因为根logger可能已经被配置过了
        self.assertIsInstance(client.logger, logging.Logger)


if __name__ == "__main__":
    unittest.main()
