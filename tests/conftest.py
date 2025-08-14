"""
测试配置和公共工具
"""
import os
import tempfile
import yaml
from typing import Dict, Any


class TestConfig:
    """测试配置管理类"""
    
    @staticmethod
    def create_base_config() -> Dict[str, Any]:
        """创建基础测试配置"""
        return {
            "llm": {
                "use": "siliconflow",
                "siliconflow": [
                    {
                        "api_key": os.getenv("SILICONFLOW_API_KEY", "sk-test-key"),
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 10
                    }
                ]
            }
        }
    
    @staticmethod
    def create_multi_provider_config() -> Dict[str, Any]:
        """创建多提供商配置（用于mock测试）"""
        return {
            "llm": {
                "use": "openai, siliconflow, anthropic, google, deepseek, zhipu",
                "openai": [
                    {
                        "api_key": "sk-mock-openai-key",
                        "api_base": "https://api.openai.com/v1",
                        "model": "gpt-4o-mini",
                        "rate_limit": 20
                    }
                ],
                "siliconflow": [
                    {
                        "api_key": os.getenv("SILICONFLOW_API_KEY", "sk-mock-sf-key-1"),
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 20
                    },
                    {
                        "api_key": "sk-mock-sf-key-2",
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions", 
                        "model": "Qwen/Qwen2.5-72B-Instruct",
                        "rate_limit": 20
                    }
                ],
                "anthropic": [
                    {
                        "api_key": "sk-ant-mock-key",
                        "api_base": "https://api.anthropic.com",
                        "model": "claude-3-5-sonnet-20241022",
                        "rate_limit": 15
                    }
                ],
                "google": [
                    {
                        "api_key": "mock-gemini-key",
                        "api_base": "https://generativelanguage.googleapis.com",
                        "model": "gemini-1.5-flash",
                        "rate_limit": 15
                    }
                ],
                "deepseek": [
                    {
                        "api_key": "sk-mock-deepseek-key",
                        "api_base": "https://api.deepseek.com/v1/chat/completions",
                        "model": "deepseek-chat", 
                        "rate_limit": 10
                    }
                ],
                "zhipu": [
                    {
                        "api_key": "mock-zhipu-key",
                        "api_base": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                        "model": "glm-4",
                        "rate_limit": 10
                    }
                ]
            }
        }
    
    @staticmethod
    def create_embedding_config() -> Dict[str, Any]:
        """创建embedding测试配置"""
        return {
            "llm": {
                "use": "openai, siliconflow, google, zhipu",
                "openai": [
                    {
                        "api_key": "sk-mock-openai-key",
                        "api_base": "https://api.openai.com/v1",
                        "model": "text-embedding-3-small",
                        "rate_limit": 20
                    }
                ],
                "siliconflow": [
                    {
                        "api_key": os.getenv("SILICONFLOW_API_KEY", "sk-mock-sf-key"),
                        "api_base": "https://api.siliconflow.cn/v1",
                        "model": "BAAI/bge-large-en-v1.5",
                        "rate_limit": 20
                    }
                ],
                "google": [
                    {
                        "api_key": "mock-gemini-key", 
                        "api_base": "https://generativelanguage.googleapis.com",
                        "model": "text-embedding-004",
                        "rate_limit": 15
                    }
                ],
                "zhipu": [
                    {
                        "api_key": "mock-zhipu-key",
                        "api_base": "https://open.bigmodel.cn/api/paas/v4",
                        "model": "embedding-2",
                        "rate_limit": 10
                    }
                ]
            }
        }

    @staticmethod
    def write_temp_config(config: Dict[str, Any]) -> str:
        """将配置写入临时文件并返回路径"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config, temp_file)
        temp_file.close()
        return temp_file.name


def mock_chat_response(content: str = "Mock response", tokens: int = 10) -> Dict[str, Any]:
    """创建mock聊天响应"""
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": tokens, "prompt_tokens": 5, "completion_tokens": 5}
    }


def mock_embedding_response(dimension: int = 384, tokens: int = 5) -> Dict[str, Any]:
    """创建mock embedding响应"""
    return {
        "data": [{"embedding": [0.1] * dimension}],
        "usage": {"total_tokens": tokens}
    }


def mock_error_response(status: int = 500, message: str = "Server Error") -> Exception:
    """创建mock错误响应"""
    from aiohttp import ClientResponseError
    from aiohttp.client_reqrep import RequestInfo
    
    # 创建一个简单的异常，避免复杂的mock
    class MockError(Exception):
        def __init__(self, status, message):
            self.status = status
            self.message = message
            super().__init__(f"{status}: {message}")
    
    return MockError(status, message)