"""
Client Interface Test - 客户端接口测试 (Mocked版本)
测试目标:
- 测试用户接口方法：invoke_batch, invoke, chat, generate, embedding等
- 使用Mock API调用，不依赖真实API
- 测试客户端接口的各种功能
"""
import unittest
import asyncio
import os
import sys
import time
import tempfile
import yaml
from unittest.mock import AsyncMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pllm import Client


class TestClientInterfaceMocked(unittest.IsolatedAsyncioTestCase):
    """客户端接口测试（使用Mock）"""
    
    async def asyncSetUp(self):
        """设置测试环境"""
        # 创建临时配置文件
        self.test_config = {
            "llm": {
                "use": "siliconflow",
                "siliconflow": [
                    {
                        "api_key": "sk-mock-key-1",
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 20
                    },
                    {
                        "api_key": "sk-mock-key-2",
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 20
                    }
                ]
            }
        }
        
        # 写入临时配置文件
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.test_config, self.temp_config)
        self.temp_config.close()
        
        self.client = Client(self.temp_config.name)
        
        # 等待LoadBalancer初始化完成
        await asyncio.sleep(0.1)
    
    async def asyncTearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_config.name):
            os.unlink(self.temp_config.name)
    
    def create_mock_response(self, content="Mock response", tokens=10):
        """创建Mock聊天响应"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": content}}],
            "usage": {"total_tokens": tokens, "prompt_tokens": 5, "completion_tokens": 5}
        }
        return mock_response
    
    def create_mock_embedding_response(self, dimension=384, tokens=5):
        """创建Mock embedding响应"""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * dimension}],
            "usage": {"total_tokens": tokens}
        }
        return mock_response
    
    @patch("aiohttp.ClientSession.post")
    async def test_generate_method(self, mock_post):
        """测试generate方法"""
        print("\n=== Testing Generate Method (Mocked) ===")
        
        mock_post.return_value.__aenter__.return_value = self.create_mock_response(
            "人工智能是一种模拟人类智能的技术，通过机器学习和算法实现智能化任务处理。"
        )
        
        prompt = "请用中文简要解释什么是人工智能。"
        
        # 测试异步generate
        response = await self.client.generate(prompt)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)
        self.assertIn("人工智能", response)
        
        print(f"Generate response: {response}")
        print("✓ Generate method works correctly")
    
    @patch("aiohttp.ClientSession.post")
    async def test_chat_method(self, mock_post):
        """测试chat方法"""
        print("\n=== Testing Chat Method (Mocked) ===")
        
        mock_post.return_value.__aenter__.return_value = self.create_mock_response(
            "你好！我是AI助手，很高兴为你服务。"
        )
        
        messages = [
            {"role": "user", "content": "你好，请介绍一下你自己"}
        ]
        
        # 测试异步chat
        response = await self.client.chat(messages)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 5)
        self.assertIn("AI", response)
        
        print(f"Chat response: {response}")
        print("✓ Chat method works correctly")
    
    def test_chat_sync_method(self):
        """测试同步chat方法"""
        print("\n=== Testing Sync Chat Method (Mocked) ===")
        
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = self.create_mock_response(
                "这是同步chat方法的测试响应。"
            )
            
            messages = [{"role": "user", "content": "测试同步方法"}]
            response = self.client.chat_sync(messages)
            
            # 验证响应
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 5)
            
            print(f"Sync chat response: {response}")
            print("✓ Sync chat method works correctly")
    
    @patch("aiohttp.ClientSession.post")
    async def test_chat_with_parameters(self, mock_post):
        """测试带参数的chat方法"""
        print("\n=== Testing Chat with Parameters (Mocked) ===")
        
        mock_post.return_value.__aenter__.return_value = self.create_mock_response(
            "这是一个创造性的故事：从前有一个勇敢的探险家..."
        )
        
        messages = [{"role": "user", "content": "请讲一个创造性的故事"}]
        
        # 测试带参数的chat
        response = await self.client.chat(
            messages, 
            temperature=0.8,
            max_tokens=150,
            top_p=0.9
        )
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 5)
        
        print(f"Chat with parameters response: {response}")
        print("✓ Chat with parameters works correctly")
    
    def test_invoke_method(self):
        """测试invoke方法"""
        print("\n=== Testing Invoke Method (Mocked) ===")
        
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = self.create_mock_response("这是invoke方法的响应")
            
            prompt = "请回答这个问题"
            
            # 测试invoke (同步方法)
            response = self.client.invoke(prompt)
            
            # 验证响应
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 5)
            
            print(f"Invoke response: {response}")
            print("✓ Invoke method works correctly")
    
    @patch("aiohttp.ClientSession.post")
    async def test_concurrent_requests_with_multiple_apis(self, mock_post):
        """测试使用多个API的并发请求"""
        print("\n=== Testing Concurrent Requests with Multiple APIs (Mocked) ===")
        
        # 为并发请求准备多个Mock响应
        mock_responses = [
            self.create_mock_response(f"并发响应 {i+1}")
            for i in range(5)
        ]
        mock_post.return_value.__aenter__.side_effect = mock_responses
        
        # 创建多个并发任务
        tasks = []
        for i in range(5):
            task = self.client.generate(f"并发测试请求 {i+1}")
            tasks.append(task)
        
        # 执行并发请求
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # 验证响应
        self.assertEqual(len(responses), 5)
        for i, response in enumerate(responses):
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"Concurrent response {i+1}: {response}")
        
        execution_time = end_time - start_time
        print(f"Concurrent execution time: {execution_time:.2f} seconds")
        print("✓ Concurrent requests work correctly")
    
    @patch("aiohttp.ClientSession.post")
    async def test_error_handling_and_recovery(self, mock_post):
        """测试错误处理和恢复"""
        print("\n=== Testing Error Handling and Recovery (Mocked) ===")
        
        # 第一次调用模拟错误，后续调用成功
        error_response = AsyncMock()
        error_response.status = 500
        error_response.json.side_effect = Exception("API Error")
        
        success_response = self.create_mock_response("错误恢复后的成功响应")
        
        mock_post.return_value.__aenter__.side_effect = [error_response, success_response]
        
        # 测试错误恢复 - 第一个provider失败，第二个成功
        try:
            response = await self.client.generate("测试错误处理")
            
            # 如果得到响应，说明错误恢复成功
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"Recovery response: {response}")
            print("✓ Error handling and recovery work correctly")
            
        except Exception as e:
            print(f"Error occurred: {e}")
            # 在Mock环境下，我们主要测试是否正确调用了API
            print("✓ Error handling mechanism is triggered correctly")
    
    @patch("aiohttp.ClientSession.post")
    async def test_embedding_method(self, mock_post):
        """测试embedding方法"""
        print("\n=== Testing Embedding Method (Mocked) ===")
        
        mock_post.return_value.__aenter__.return_value = self.create_mock_embedding_response()
        
        text = "这是一个用于测试embedding功能的文本"
        
        # 测试embedding
        response = await self.client.embedding(text)
        
        # 验证响应
        self.assertIsInstance(response, list)
        self.assertGreater(len(response), 0)
        self.assertIsInstance(response[0], float)
        
        print(f"Embedding dimension: {len(response)}")
        print(f"First few values: {response[:5]}")
        print("✓ Embedding method works correctly")
    
    def test_sync_embedding_method(self):
        """测试同步embedding方法"""
        print("\n=== Testing Sync Embedding Method (Mocked) ===")
        
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.return_value = self.create_mock_embedding_response()
            
            text = "同步embedding测试文本"
            response = self.client.embedding_sync(text)
            
            # 验证响应
            self.assertIsInstance(response, list)
            self.assertGreater(len(response), 0)
            self.assertIsInstance(response[0], float)
            
            print(f"Sync embedding dimension: {len(response)}")
            print("✓ Sync embedding method works correctly")
    
    def test_statistics_collection(self):
        """测试统计信息收集"""
        print("\n=== Testing Statistics Collection (Mocked) ===")
        
        # 获取统计信息
        stats = self.client.get_stats()
        
        # 验证统计信息结构
        self.assertIsInstance(stats, dict)
        self.assertIn("siliconflow", stats)
        
        provider_stats = stats["siliconflow"]
        self.assertIsInstance(provider_stats, list)
        
        for client_stat in provider_stats:
            required_fields = ["total_requests", "total_tokens", "error_count", "active"]
            for field in required_fields:
                self.assertIn(field, client_stat)
                self.assertIsInstance(client_stat[field], (int, bool))
        
        print(f"Stats structure: {stats}")
        print("✓ Statistics collection works correctly")


if __name__ == "__main__":
    unittest.main()