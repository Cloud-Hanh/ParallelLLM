"""
Client Interface Test - 客户端接口测试
测试目标:
- 测试用户接口方法：invoke_batch, invoke, chat, generate, embedding等
- 使用真实API调用，加载input/config/pllm.yaml配置
- 利用多个API key进行测试
- 单次测试保证质量，不进行循环测试
"""
import unittest
import asyncio
import os
import sys
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pllm import Client


class TestClientInterface(unittest.IsolatedAsyncioTestCase):
    """客户端接口测试"""
    
    async def asyncSetUp(self):
        """设置测试环境"""
        self.config_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "input", 
            "config", 
            "pllm.yaml"
        )
        self.client = Client(self.config_path)
        
        # 等待LoadBalancer初始化完成
        await asyncio.sleep(0.1)
    
    async def test_generate_method(self):
        """测试generate方法"""
        print("\n=== Testing Generate Method ===")
        
        prompt = "请用中文简要解释什么是人工智能。"
        
        # 测试异步generate
        response = await self.client.generate(prompt)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)
        self.assertIn("人工智能", response)
        
        print(f"Generate response: {response[:100]}...")
        print("✓ Generate method works correctly")
    
    def test_generate_sync_method(self):
        """测试同步generate方法"""
        print("\n=== Testing Generate Sync Method ===")
        
        prompt = "2+2等于多少？请直接回答数字。"
        
        # 测试同步generate
        response = self.client.generate_sync(prompt)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"Generate sync response: {response}")
        print("✓ Generate sync method works correctly")
    
    async def test_chat_method(self):
        """测试chat方法"""
        print("\n=== Testing Chat Method ===")
        
        messages = [
            {"role": "system", "content": "你是一个有用的助手，请用中文回答。"},
            {"role": "user", "content": "请简单介绍一下Python编程语言的特点。"}
        ]
        
        # 测试异步chat
        response = await self.client.chat(messages)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 20)
        self.assertIn("Python", response)
        
        print(f"Chat response: {response[:100]}...")
        print("✓ Chat method works correctly")
    
    def test_chat_sync_method(self):
        """测试同步chat方法"""
        print("\n=== Testing Chat Sync Method ===")
        
        messages = [
            {"role": "user", "content": "1+1=? 请只回答数字。"}
        ]
        
        # 测试同步chat
        response = self.client.chat_sync(messages)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"Chat sync response: {response}")
        print("✓ Chat sync method works correctly")
    
    def test_invoke_method(self):
        """测试invoke方法"""
        print("\n=== Testing Invoke Method ===")
        
        prompt = "什么是机器学习？请用一句话概括。"
        
        # 测试invoke（应该是generate的同步版本）
        response = self.client.invoke(prompt)
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 10)
        self.assertIn("机器学习", response)
        
        print(f"Invoke response: {response}")
        print("✓ Invoke method works correctly")
    
    def test_invoke_batch_method(self):
        """测试invoke_batch方法"""
        print("\n=== Testing Invoke Batch Method ===")
        
        prompts = [
            "1+2=?",
            "3+4=?", 
            "5+6=?"
        ]
        
        # 测试批量invoke
        responses = self.client.invoke_batch(prompts)
        
        # 验证响应
        self.assertIsInstance(responses, list)
        self.assertEqual(len(responses), 3)
        
        for i, response in enumerate(responses):
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"Batch response {i+1}: {response}")
        
        print("✓ Invoke batch method works correctly")
    
    async def test_chat_with_parameters(self):
        """测试带参数的chat方法"""
        print("\n=== Testing Chat with Parameters ===")
        
        messages = [
            {"role": "user", "content": "请生成5个随机数字，用逗号分隔。"}
        ]
        
        # 测试带温度参数的chat
        response = await self.client.chat(
            messages, 
            temperature=0.8,
            max_tokens=50
        )
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"Chat with params response: {response}")
        print("✓ Chat with parameters works correctly")
    
    async def test_generate_with_retry_policy(self):
        """测试带重试策略的generate方法"""
        print("\n=== Testing Generate with Retry Policy ===")
        
        prompt = "请解释什么是深度学习？"
        
        # 测试不同的重试策略
        response_fixed = await self.client.generate(prompt, retry_policy="fixed")
        response_retry_once = await self.client.generate(prompt, retry_policy="retry_once")
        
        # 验证响应
        self.assertIsInstance(response_fixed, str)
        self.assertIsInstance(response_retry_once, str)
        self.assertGreater(len(response_fixed), 10)
        self.assertGreater(len(response_retry_once), 10)
        
        print(f"Fixed retry response: {response_fixed[:50]}...")
        print(f"Retry once response: {response_retry_once[:50]}...")
        print("✓ Retry policies work correctly")
    
    async def test_concurrent_requests_with_multiple_apis(self):
        """测试使用多个API的并发请求"""
        print("\n=== Testing Concurrent Requests with Multiple APIs ===")
        
        # 准备不同类型的请求
        tasks = [
            self.client.generate("计算 10 + 15 = ?"),
            self.client.chat([{"role": "user", "content": "什么是区块链？一句话概括。"}]),
            self.client.generate("解释量子计算的基本概念"),
            self.client.chat([{"role": "user", "content": "Python和Java的主要区别是什么？"}]),
        ]
        
        # 记录开始时间
        start_time = time.time()
        
        # 并发执行
        responses = await asyncio.gather(*tasks)
        
        # 记录结束时间
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 验证所有响应
        self.assertEqual(len(responses), 4)
        for i, response in enumerate(responses):
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 5)
            print(f"Concurrent request {i+1}: {response[:50]}...")
        
        print(f"Concurrent execution time: {execution_time:.2f} seconds")
        print("✓ Concurrent requests with multiple APIs work correctly")
    
    def test_get_stats_method(self):
        """测试get_stats方法"""
        print("\n=== Testing Get Stats Method ===")
        
        # 先执行一些请求来生成统计数据
        self.client.invoke("测试统计")
        
        # 获取统计信息
        stats = self.client.get_stats()
        
        # 验证统计结构
        self.assertIsInstance(stats, dict)
        self.assertIn("siliconflow", stats)
        
        # 验证每个provider的统计信息
        for provider_name, provider_stats in stats.items():
            self.assertIsInstance(provider_stats, list)
            
            for client_stat in provider_stats:
                # 验证必要字段
                required_fields = ["total_requests", "total_tokens", "error_count", "active", "model"]
                for field in required_fields:
                    self.assertIn(field, client_stat)
                
                # 验证数据类型
                self.assertIsInstance(client_stat["total_requests"], int)
                self.assertIsInstance(client_stat["total_tokens"], int)
                self.assertIsInstance(client_stat["error_count"], int)
                self.assertIsInstance(client_stat["active"], bool)
                
                print(f"Provider {provider_name}: {client_stat}")
        
        print("✓ Get stats method works correctly")
    
    async def test_mixed_sync_async_usage(self):
        """测试混合使用同步和异步方法"""
        print("\n=== Testing Mixed Sync/Async Usage ===")
        
        # 异步请求
        async_response = await self.client.generate("异步测试：1+1=?")
        
        # 同步请求
        sync_response = self.client.generate_sync("同步测试：2+2=?")
        
        # 批量同步请求
        batch_responses = self.client.invoke_batch([
            "批量测试1：3+3=?",
            "批量测试2：4+4=?"
        ])
        
        # 验证所有响应
        self.assertIsInstance(async_response, str)
        self.assertIsInstance(sync_response, str)
        self.assertIsInstance(batch_responses, list)
        self.assertEqual(len(batch_responses), 2)
        
        print(f"Async response: {async_response}")
        print(f"Sync response: {sync_response}")
        print(f"Batch responses: {batch_responses}")
        print("✓ Mixed sync/async usage works correctly")
    
    async def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        print("\n=== Testing Error Handling and Recovery ===")
        
        # 测试正常请求
        normal_response = await self.client.generate("这是一个正常的请求")
        self.assertIsInstance(normal_response, str)
        self.assertGreater(len(normal_response), 0)
        
        # 测试空prompt（应该能处理）
        try:
            empty_response = await self.client.generate("")
            print(f"Empty prompt response: {empty_response}")
        except Exception as e:
            print(f"Empty prompt handled with error: {e}")
        
        # 测试超长prompt（应该能处理或给出合理错误）
        long_prompt = "测试" * 1000  # 创建一个很长的prompt
        try:
            long_response = await self.client.generate(long_prompt)
            print(f"Long prompt response: {long_response[:50]}...")
        except Exception as e:
            print(f"Long prompt handled with error: {e}")
        
        # 验证系统仍然能正常工作
        recovery_response = await self.client.generate("恢复测试：系统是否正常？")
        self.assertIsInstance(recovery_response, str)
        self.assertGreater(len(recovery_response), 0)
        
        print(f"Recovery response: {recovery_response}")
        print("✓ Error handling and recovery work correctly")


if __name__ == "__main__":
    unittest.main()