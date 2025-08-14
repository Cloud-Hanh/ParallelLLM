"""
SiliconFlow Provider测试
"""
import os
import sys

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from base_test import BaseProviderTest


class TestSiliconFlowProvider(BaseProviderTest):
    """SiliconFlow提供商测试"""
    
    @property
    def provider_name(self) -> str:
        return "siliconflow"
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.siliconflow.cn/v1/chat/completions"
    
    def _get_default_model(self) -> str:
        return "deepseek-ai/DeepSeek-V2.5"
    
    def _create_provider_config(self):
        """使用真实API密钥或mock密钥"""
        api_key = os.getenv("SILICONFLOW_API_KEY", "sk-mock-siliconflow-key")
        return {
            "llm": {
                "use": "siliconflow",
                "siliconflow": [
                    {
                        "api_key": api_key,
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 20
                    }
                ]
            }
        }


class TestSiliconFlowEmbeddingProvider(BaseProviderTest):
    """SiliconFlow Embedding测试"""
    
    @property
    def provider_name(self) -> str:
        return "siliconflow"
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.siliconflow.cn/v1"
    
    def _get_default_model(self) -> str:
        return "BAAI/bge-large-en-v1.5"
    
    def _create_provider_config(self):
        """为embedding创建配置"""
        api_key = os.getenv("SILICONFLOW_API_KEY", "sk-mock-siliconflow-key")
        return {
            "llm": {
                "use": "siliconflow", 
                "siliconflow": [
                    {
                        "api_key": api_key,
                        "api_base": "https://api.siliconflow.cn/v1",
                        "model": "BAAI/bge-large-en-v1.5",
                        "rate_limit": 20
                    }
                ]
            }
        }


class TestSiliconFlowMultiModel(BaseProviderTest):
    """SiliconFlow多模型测试"""
    
    @property
    def provider_name(self) -> str:
        return "siliconflow"
    
    @property
    def supports_embedding(self) -> bool:
        return False
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.siliconflow.cn/v1/chat/completions"
    
    def _get_default_model(self) -> str:
        return "Qwen/Qwen2.5-72B-Instruct"
    
    def _create_provider_config(self):
        """多密钥、多模型配置"""
        api_key = os.getenv("SILICONFLOW_API_KEY", "sk-mock-siliconflow-key")
        return {
            "llm": {
                "use": "siliconflow",
                "siliconflow": [
                    {
                        "api_key": api_key,
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "deepseek-ai/DeepSeek-V2.5",
                        "rate_limit": 20
                    },
                    {
                        "api_key": "sk-mock-key-2",
                        "api_base": "https://api.siliconflow.cn/v1/chat/completions",
                        "model": "Qwen/Qwen2.5-72B-Instruct", 
                        "rate_limit": 20
                    }
                ]
            }
        }


if __name__ == "__main__":
    import unittest
    unittest.main()