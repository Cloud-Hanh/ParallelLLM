"""
Anthropic Provider测试
"""
import os
import sys

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_base_provider import BaseProviderTest


class TestAnthropicProvider(BaseProviderTest):
    """Anthropic提供商测试"""
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def supports_embedding(self) -> bool:
        return False  # Anthropic不支持embedding
    
    @property
    def mock_api_base(self) -> str:
        return "https://api.anthropic.com"
    
    def _get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"


if __name__ == "__main__":
    import unittest
    unittest.main()