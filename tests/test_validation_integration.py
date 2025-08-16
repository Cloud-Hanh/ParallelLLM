#!/usr/bin/env python3
"""
Output Validation Integration Tests - 输出验证集成测试

这个文件测试输出验证功能是否能够真正约束LLM的输出。
使用真实的API调用来验证JSON、文本和正则表达式验证器的效果。

前置条件:
- 需要设置 SILICONFLOW_API_KEY 环境变量
- 使用真实API调用，会产生费用
"""

import os
import sys
import tempfile
import unittest
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pllm import Client
from src.pllm.validators import JsonValidator, TextValidator, RegexValidator


class TestValidationIntegration(unittest.IsolatedAsyncioTestCase):
    """输出验证集成测试"""
    
    async def asyncSetUp(self):
        """设置测试环境"""
        # 首先尝试使用配置文件中的API密钥
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "input", "config", "pllm.yaml")
        
        if os.path.exists(self.config_path):
            # 直接使用配置文件
            self.client = Client(self.config_path)
            self.use_config_file = True
            print(f"✅ 使用配置文件: {self.config_path}")
        else:
            # 回退到环境变量方式
            self.api_key = os.getenv("SILICONFLOW_API_KEY")
            if not self.api_key:
                self.skipTest("需要 input/config/pllm.yaml 配置文件或 SILICONFLOW_API_KEY 环境变量")
            
            # 创建临时配置文件
            self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
            config_content = f"""
llm:
  use: "siliconflow"
  siliconflow:
    - api_key: "{self.api_key}"
      api_base: "https://api.siliconflow.cn/v1"
      model: "deepseek-ai/DeepSeek-V2.5"
      rate_limit: 20
"""
            self.temp_config.write(config_content)
            self.temp_config.close()
            
            # 创建客户端
            self.client = Client(self.temp_config.name)
            self.use_config_file = False
            print(f"⚠️  使用环境变量创建临时配置")
        
        # 等待初始化完成
        await asyncio.sleep(0.1)
    
    async def asyncTearDown(self):
        """清理测试环境"""
        # 只有使用临时配置文件时才需要清理
        if hasattr(self, 'use_config_file') and not self.use_config_file:
            if hasattr(self, 'temp_config'):
                os.unlink(self.temp_config.name)
    
    async def test_json_validator_constraint(self):
        """测试JSON验证器是否能约束LLM输出格式"""
        print("\n=== Testing JSON Validator Constraint ===")
        
        # 创建JSON验证器（允许提取JSON）
        json_validator = JsonValidator(max_retries=3, strict=False, extract_json=True)
        
        # 要求返回JSON格式的用户信息
        prompt = """请返回一个包含以下字段的JSON对象：
- name: 字符串类型的姓名
- age: 数字类型的年龄
- skills: 字符串数组类型的技能列表

请只返回JSON，不要包含其他文字说明。"""
        
        try:
            result = await self.client.generate(prompt, output_validator=json_validator)
            print(f"生成结果: {result}")
            
            # 验证结果是有效的JSON
            import json
            parsed = json.loads(result)
            
            # 验证包含期望的字段
            self.assertIn('name', parsed)
            self.assertIn('age', parsed)
            self.assertIn('skills', parsed)
            
            # 验证数据类型
            self.assertIsInstance(parsed['name'], str)
            self.assertIsInstance(parsed['age'], (int, float))
            self.assertIsInstance(parsed['skills'], list)
            
            print("✅ JSON验证器成功约束了LLM输出格式")
            
        except Exception as e:
            self.fail(f"JSON验证器测试失败: {e}")
    
    async def test_json_validator_with_schema(self):
        """测试带Schema的JSON验证器"""
        print("\n=== Testing JSON Schema Validator ===")
        
        try:
            import jsonschema
            
            # 定义严格的JSON Schema
            schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "age": {"type": "integer", "minimum": 0, "maximum": 150},
                    "email": {"type": "string", "format": "email"},
                    "hobbies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1
                    }
                },
                "required": ["name", "age", "email", "hobbies"],
                "additionalProperties": False
            }
            
            json_validator = JsonValidator(schema=schema, max_retries=3)
            
            prompt = """请严格按照以下要求返回JSON：
{
  "name": "有效的姓名字符串",
  "age": 有效的整数年龄(0-150),
  "email": "有效的邮箱地址",
  "hobbies": ["爱好1", "爱好2"]
}

只返回JSON，不要其他内容。"""
            
            result = await self.client.generate(prompt, output_validator=json_validator)
            print(f"Schema验证结果: {result}")
            
            # 验证Schema
            import json
            parsed = json.loads(result)
            jsonschema.validate(parsed, schema)
            
            print("✅ JSON Schema验证器成功约束了LLM输出")
            
        except ImportError:
            self.skipTest("jsonschema未安装，跳过Schema测试")
        except Exception as e:
            self.fail(f"JSON Schema验证器测试失败: {e}")
    
    async def test_text_validator_constraint(self):
        """测试文本验证器是否能约束LLM输出内容"""
        print("\n=== Testing Text Validator Constraint ===")
        
        def check_contains_keywords(text):
            """检查文本是否包含必要的关键词"""
            required_keywords = ["Python", "机器学习", "数据科学"]
            return all(keyword in text for keyword in required_keywords)
        
        text_validator = TextValidator(
            requirements="回答必须包含: Python, 机器学习, 数据科学 这三个关键词",
            validator_func=check_contains_keywords,
            max_retries=3
        )
        
        prompt = """请用一段话介绍一个技术领域。要求：
1. 必须提到Python语言
2. 必须提到机器学习概念  
3. 必须提到数据科学领域
4. 回答要自然流畅"""
        
        try:
            result = await self.client.generate(prompt, output_validator=text_validator)
            print(f"文本验证结果: {result}")
            
            # 验证包含所有必要关键词
            self.assertIn("Python", result)
            self.assertIn("机器学习", result) 
            self.assertIn("数据科学", result)
            
            print("✅ 文本验证器成功约束了LLM输出内容")
            
        except Exception as e:
            self.fail(f"文本验证器测试失败: {e}")
    
    async def test_regex_validator_constraint(self):
        """测试正则表达式验证器是否能约束LLM输出格式"""
        print("\n=== Testing Regex Validator Constraint ===")
        
        # 要求电话号码格式
        phone_pattern = r'^\+86-1[3-9]\d{9}$'
        regex_validator = RegexValidator(
            pattern=phone_pattern,
            requirements_description="必须是中国大陆手机号格式: +86-1xxxxxxxxx",
            max_retries=3
        )
        
        prompt = """请生成一个中国大陆的手机号码。
格式要求: +86-1xxxxxxxxx (其中x为数字)
只返回手机号码，不要其他内容。"""
        
        try:
            result = await self.client.generate(prompt, output_validator=regex_validator)
            print(f"正则验证结果: {result}")
            
            # 验证格式匹配
            import re
            self.assertTrue(re.match(phone_pattern, result.strip()))
            
            print("✅ 正则表达式验证器成功约束了LLM输出格式")
            
        except Exception as e:
            self.fail(f"正则表达式验证器测试失败: {e}")
    
    async def test_validation_retry_behavior(self):
        """测试验证器的重试行为"""
        print("\n=== Testing Validation Retry Behavior ===")
        
        # 创建一个真正不可能满足的验证器来测试重试
        def impossible_validator(text):
            """真正不可能满足的验证条件"""
            return "极其特殊不可能出现的字符串ABCXYZ999888777" in text and len(text) < 5
        
        text_validator = TextValidator(
            requirements="必须包含'极其特殊不可能出现的字符串ABCXYZ999888777'且文本长度少于5个字符",
            validator_func=impossible_validator,
            max_retries=2  # 限制重试次数
        )
        
        prompt = "请随便说点什么。"
        
        try:
            result = await self.client.generate(prompt, output_validator=text_validator)
            # 如果到这里说明验证意外成功了
            self.fail("验证器应该失败但却成功了")
        except ValueError as e:
            # 期望的失败情况
            self.assertIn("Output validation failed after", str(e))
            print("✅ 验证器正确处理了重试失败情况")
    
    async def test_validation_statistics(self):
        """测试验证功能的统计信息"""
        print("\n=== Testing Validation Statistics ===")
        
        json_validator = JsonValidator(max_retries=2)
        
        # 获取初始统计
        initial_stats = self.client.get_stats()
        initial_requests = sum(provider['total_requests'] for providers in initial_stats.values() for provider in providers)
        
        prompt = """返回JSON格式: {"message": "hello", "count": 1}"""
        
        try:
            await self.client.generate(prompt, output_validator=json_validator)
            
            # 获取验证后统计
            final_stats = self.client.get_stats()
            final_requests = sum(provider['total_requests'] for providers in final_stats.values() for provider in providers)
            
            # 验证请求数量变化
            self.assertGreaterEqual(final_requests, initial_requests + 1)
            print(f"请求数量从 {initial_requests} 增加到 {final_requests}")
            print("✅ 验证功能正确记录了统计信息")
            
        except Exception as e:
            self.fail(f"统计信息测试失败: {e}")


if __name__ == "__main__":
    # 当直接运行文件时，使用标准unittest运行器
    unittest.main(verbosity=2)