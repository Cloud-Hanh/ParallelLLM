"""
OpenAI Provider测试
"""
import os
import sys

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_base_provider import BaseProviderTest


class TestOpenAIProvider(BaseProviderTest):
    """OpenAI提供商测试"""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property 
    def supports_embedding(self) -> bool:
        return True
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.openai.com/v1"
    
    def _get_default_model(self) -> str:
        return "gpt-4o-mini"


class TestOpenAIEmbeddingProvider(BaseProviderTest):
    """OpenAI Embedding专用测试"""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.openai.com/v1"
    
    def _get_default_model(self) -> str:
        return "text-embedding-3-small"
    
    def _create_provider_config(self):
        """为embedding创建专用配置"""
        return {
            "llm": {
                "use": "openai",
                "openai": [
                    {
                        "api_key": "sk-mock-openai-key",
                        "api_base": "https://api.openai.com/v1",
                        "model": "text-embedding-3-small",
                        "rate_limit": 20
                    }
                ]
            }
        }


if __name__ == "__main__":
    import unittest
    unittest.main()