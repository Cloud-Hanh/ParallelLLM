"""
Zhipu AI Provider测试
"""
import os
import sys

# 添加项目根目录和tests目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

from base_test import BaseProviderTest


class TestZhipuProvider(BaseProviderTest):
    """Zhipu提供商测试"""
    
    @property
    def provider_name(self) -> str:
        return "zhipu"
    
    @property
    def supports_embedding(self) -> bool:
        return True
    
    @property
    def mock_api_base(self) -> str:
        return "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    
    def _get_default_model(self) -> str:
        return "glm-4"


if __name__ == "__main__":
    import unittest
    unittest.main()