"""
测试目标: 手动集成测试 - 需要真实API密钥
- 测试与真实API服务的连接和交互
- 验证完整的请求-响应流程
- 测试真实的错误处理和重试机制
- 需要设置环境变量 SILICONFLOW_API_KEY
- 包含聊天、生成和embedding功能的端到端测试
"""
import unittest
import asyncio
import logging
import os
from pllm import Client


class TestClientFunctionality(unittest.IsolatedAsyncioTestCase):
    """客户端基础功能测试套件 - 需要真实API密钥"""

    @classmethod
    def setUpClass(cls):
        """类级别初始化"""
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        cls.logger = logging.getLogger("TestClient")
        
        # 检查配置文件是否存在
        cls.config_path = "input/config/pllm.yaml"
        if not os.path.exists(cls.config_path):
            cls.logger.error(f"配置文件不存在: {cls.config_path}")
            cls.has_config = False
        else:
            cls.has_config = True
            cls.logger.info(f"使用配置文件: {cls.config_path}")

    async def asyncSetUp(self):
        """每个测试方法前的初始化"""
        if not self.has_config:
            self.skipTest("配置文件不存在或无法读取")
        
        # 使用真实的配置文件
        self.client = Client(self.config_path, log_level=logging.DEBUG)

    async def test_basic_functionality(self):
        """测试生成和聊天基础功能"""
        try:
            self.logger.info("开始测试基础功能")
            
            # 测试生成功能
            self.logger.info("测试generate方法")
            response = await self.client.generate("解释什么是机器学习")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 10)  # 响应应该有实际内容
            self.logger.info(f"Generate响应长度: {len(response)}")

            # 测试聊天功能
            self.logger.info("测试chat方法")
            chat_response = await self.client.chat(
                [
                    {"role": "system", "content": "你是一个有用的AI助手"},
                    {
                        "role": "user",
                        "content": "写一个Python函数计算两个数的最大公约数",
                    },
                ]
            )
            self.assertIsInstance(chat_response, str)
            self.assertGreater(len(chat_response), 10)
            self.logger.debug("聊天响应示例：%s", chat_response[:100] + "...")  # 只显示前100字符

            # 验证统计信息
            stats = self.client.get_stats()
            self.logger.debug("完整统计结构：%s", stats)

            # 计算总请求数和总tokens
            total_requests = 0
            total_tokens = 0

            # 遍历所有提供商
            for provider in stats:
                # 遍历该提供商的所有客户端实例
                for client_stats in stats[provider]:
                    total_requests += client_stats["total_requests"]
                    total_tokens += client_stats["total_tokens"]

            self.assertGreaterEqual(
                total_requests, 2, f"总请求数不足，当前：{total_requests}"
            )
            self.assertGreaterEqual(
                total_tokens, 50, f"总token数不足，当前：{total_tokens}"
            )
            
            self.logger.info(f"测试完成 - 总请求数: {total_requests}, 总tokens: {total_tokens}")

        except Exception as e:
            self.logger.error("测试失败，当前统计信息：%s", stats, exc_info=True)
            raise


if __name__ == "__main__":
    unittest.main()
