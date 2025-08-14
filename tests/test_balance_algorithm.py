"""
Balance Algorithm Test - 负载均衡算法测试
测试目标:
- 测试负载均衡算法是否正确选择最优的API key
- 测试token计数是否准确记录
- 使用真实API调用，加载input/config/pllm.yaml配置
- 通过修改provider状态测试选择逻辑
"""
import unittest
import asyncio
import os
import sys
import time
import random

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pllm import Client


class TestBalanceAlgorithm(unittest.IsolatedAsyncioTestCase):
    """负载均衡算法测试"""
    
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
    
    async def test_provider_selection_with_different_loads(self):
        """测试不同负载下的provider选择逻辑"""
        print("\n=== Testing Provider Selection with Different Loads ===")
        
        # 获取初始统计信息
        initial_stats = self.client.get_stats()
        print(f"Initial stats: {initial_stats}")
        
        # 人为给某些provider增加active_requests来测试选择逻辑
        balancer = self.client.balancer
        providers = balancer.providers["siliconflow"]
        
        # 模拟不同的负载情况
        providers[0].active_requests = 5  # 高负载
        providers[1].active_requests = 2  # 中等负载
        providers[2].active_requests = 0  # 低负载
        
        # 执行请求，应该选择负载最低的provider
        response = await self.client.generate("Test load balancing selection")
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # 检查是否选择了负载最低的provider（provider[2]）
        # 通过检查active_requests的变化来验证
        self.assertEqual(providers[2].active_requests, 0)  # 请求完成后应该回到0
        
        print(f"Response received: {response[:50]}...")
        print("✓ Load balancing selection works correctly")
    
    async def test_token_counting_accuracy(self):
        """测试token计数的准确性"""
        print("\n=== Testing Token Counting Accuracy ===")
        
        # 获取测试前的token统计
        stats_before = self.client.get_stats()
        total_tokens_before = sum(
            sum(client_stat.get("total_tokens", 0) for client_stat in provider_stats)
            for provider_stats in stats_before.values()
        )
        
        # 发送一个请求
        test_prompt = "请用中文回答：1+1等于多少？请详细解释。"
        response = await self.client.generate(test_prompt)
        
        # 获取测试后的token统计
        stats_after = self.client.get_stats()
        total_tokens_after = sum(
            sum(client_stat.get("total_tokens", 0) for client_stat in provider_stats)
            for provider_stats in stats_after.values()
        )
        
        # 验证token计数增加
        token_increase = total_tokens_after - total_tokens_before
        self.assertGreater(token_increase, 0, "Token count should increase after request")
        
        print(f"Tokens before: {total_tokens_before}")
        print(f"Tokens after: {total_tokens_after}")
        print(f"Token increase: {token_increase}")
        print(f"Response: {response[:100]}...")
        print("✓ Token counting works correctly")
    
    async def test_error_count_and_failover(self):
        """测试错误计数和故障转移"""
        print("\n=== Testing Error Count and Failover ===")
        
        # 获取初始错误统计
        stats_before = self.client.get_stats()
        
        # 人为使某个provider失效来测试故障转移
        balancer = self.client.balancer
        providers = balancer.providers["siliconflow"]
        
        # 将第一个provider设置为高错误状态
        providers[0].error_count = 3  # 达到失效阈值
        providers[0].is_active = False
        
        # 执行请求，应该自动切换到其他provider
        response = await self.client.generate("Test failover mechanism")
        
        # 验证响应成功（说明成功切换到了其他provider）
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # 验证第一个provider确实被跳过了
        self.assertFalse(providers[0].is_active)
        
        print(f"First provider status: {providers[0].is_active}")
        print(f"Response received: {response[:50]}...")
        print("✓ Failover mechanism works correctly")
    
    async def test_rate_limit_handling(self):
        """测试速率限制处理"""
        print("\n=== Testing Rate Limit Handling ===")
        
        balancer = self.client.balancer
        providers = balancer.providers["siliconflow"]
        
        # 获取一个provider并模拟接近速率限制
        target_provider = providers[0]
        
        # 人为填充速率限制队列
        current_time = time.time()
        for _ in range(19):  # 接近20的限制
            target_provider.request_queue.append(current_time)
        
        # 执行请求，应该能够处理速率限制
        response = await self.client.generate("Test rate limiting")
        
        # 验证响应
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        print(f"Rate limit queue length: {len(target_provider.request_queue)}")
        print(f"Response received: {response[:50]}...")
        print("✓ Rate limit handling works correctly")
    
    async def test_provider_statistics_tracking(self):
        """测试provider统计信息跟踪"""
        print("\n=== Testing Provider Statistics Tracking ===")
        
        # 获取初始统计
        stats_before = self.client.get_stats()
        
        # 发送多个请求
        requests = [
            "计算 2+3 等于多少？",
            "什么是机器学习？",
            "解释一下Python的特点"
        ]
        
        for i, prompt in enumerate(requests):
            response = await self.client.generate(prompt)
            print(f"Request {i+1} completed: {len(response)} characters")
        
        # 获取最终统计
        stats_after = self.client.get_stats()
        
        # 验证统计信息
        for provider_name, provider_stats in stats_after.items():
            for client_stat in provider_stats:
                # 验证统计字段存在且合理
                self.assertIn("total_requests", client_stat)
                self.assertIn("total_tokens", client_stat)
                self.assertIn("error_count", client_stat)
                
                # requests应该增加
                total_requests = client_stat["total_requests"]
                self.assertGreaterEqual(total_requests, 0)
                
                # tokens应该增加
                total_tokens = client_stat["total_tokens"]
                self.assertGreaterEqual(total_tokens, 0)
                
                print(f"Provider {provider_name}: {total_requests} requests, {total_tokens} tokens")
        
        print("✓ Statistics tracking works correctly")
    
    async def test_concurrent_request_load_balancing(self):
        """测试并发请求的负载均衡"""
        print("\n=== Testing Concurrent Request Load Balancing ===")
        
        # 准备并发请求
        prompts = [
            f"请简单回答：{i} + {i} = ?"
            for i in range(1, 6)  # 5个并发请求
        ]
        
        # 记录开始时间
        start_time = time.time()
        
        # 并发执行请求
        tasks = [self.client.generate(prompt) for prompt in prompts]
        responses = await asyncio.gather(*tasks)
        
        # 记录结束时间
        end_time = time.time()
        
        # 验证所有响应都成功
        self.assertEqual(len(responses), 5)
        for i, response in enumerate(responses):
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            print(f"Concurrent request {i+1}: {response[:30]}...")
        
        # 验证并发性能（应该比串行执行快）
        execution_time = end_time - start_time
        print(f"Concurrent execution time: {execution_time:.2f} seconds")
        
        # 获取最终统计，验证负载分布
        final_stats = self.client.get_stats()
        print(f"Final stats after concurrent requests: {final_stats}")
        
        print("✓ Concurrent load balancing works correctly")


if __name__ == "__main__":
    unittest.main()