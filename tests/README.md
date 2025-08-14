# ParallelLLM 测试指南

欢迎查看 ParallelLLM 的测试指南！本文档详细说明如何运行和理解项目的测试套件。

## 快速开始

**最常用的测试命令：**

```bash
# 运行单元测试（不需要API密钥，最快）
python tests/run_tests.py --unit

# 运行所有测试
python tests/run_tests.py --all

# 运行集成测试（需要真实API密钥）
export SILICONFLOW_API_KEY="your-api-key"
python tests/run_tests.py --integration
```

## 测试架构概述

本项目采用分层测试架构，包含单元测试、集成测试和提供商特定测试，确保所有功能模块的可靠性。

## 测试文件结构

```
tests/
├── conftest.py                    # 测试配置和公共工具
├── run_tests.py                   # 测试运行脚本
├── test_base_provider.py          # Provider测试基类
├── test_client.py                 # Client核心功能测试
├── test_load_balancing.py         # 负载均衡和高级功能测试
├── manual_test.py                 # 手动集成测试（需要真实API密钥）
├── multi_key_test.py              # 多密钥负载均衡测试
└── provider_tests/                # 各提供商专门测试
    ├── test_openai_provider.py
    ├── test_siliconflow_provider.py
    ├── test_anthropic_provider.py
    ├── test_google_provider.py
    ├── test_deepseek_provider.py
    └── test_zhipu_provider.py
```

## 测试类型

### 1. 单元测试（Unit Tests）
使用Mock API调用，不需要真实密钥

**测试内容：**
- Client接口功能（chat, generate, embedding, invoke系列）
- 同步/异步方法
- 错误处理
- 参数传递
- 统计信息收集

**运行方式：**
```bash
python tests/run_tests.py --unit
```

### 2. 提供商测试（Provider Tests）
每个提供商的专门测试

**支持的提供商：**
- **OpenAI** - 支持chat + embedding
- **SiliconFlow** - 支持chat + embedding  
- **Anthropic** - 仅支持chat
- **Google** - 支持chat + embedding
- **DeepSeek** - 仅支持chat
- **Zhipu** - 支持chat + embedding

**运行方式：**
```bash
# 测试特定提供商
python tests/run_tests.py --provider openai
python tests/run_tests.py --provider siliconflow
```

### 3. 负载均衡测试（Load Balancing Tests）
测试高级功能和系统级行为

**测试内容：**
- 多提供商负载均衡
- 故障转移（failover）
- 重试策略（retry_once, fixed, infinite）
- 并发请求处理
- 速率限制
- 健康检查

### 4. 集成测试（Integration Tests）
使用真实API密钥测试实际功能

**前置条件：**
```bash
export SILICONFLOW_API_KEY="your-api-key"
```

**运行方式：**
```bash
python tests/run_tests.py --integration
```

## 测试配置

### 测试用配置文件
`conftest.py` 提供了统一的配置管理：

```python
# 基础单提供商配置
TestConfig.create_base_config()

# 多提供商配置（用于负载均衡测试）
TestConfig.create_multi_provider_config()

# Embedding专用配置
TestConfig.create_embedding_config()
```

### Mock响应工具
```python
# Mock聊天响应
mock_chat_response(content="响应内容", tokens=10)

# Mock embedding响应  
mock_embedding_response(dimension=384, tokens=5)

# Mock错误响应
mock_error_response(status=500, message="错误信息")
```

## 运行测试

### 开发者常用命令

```bash
# 最基础：运行单元测试（无需API密钥，速度最快）
python tests/run_tests.py --unit

# 开发时：运行核心客户端测试
python -m unittest tests.test_client.TestPLLMClient

# 调试时：运行单个测试方法并查看详细输出
python -m unittest tests.test_client.TestPLLMClient.test_generate -v

# 集成测试：验证实际API调用（需要真实密钥）
export SILICONFLOW_API_KEY="your-api-key"
python tests/manual_test.py

# 完整测试：运行所有测试
python tests/run_tests.py --all
```

### 测试环境设置

**前置条件：**
```bash
# 安装项目依赖
pip install -e .
pip install -r requirements.txt

# 设置API密钥（仅集成测试需要）
export SILICONFLOW_API_KEY="your-siliconflow-api-key"
```

### 详细测试选项
```bash
# 查看所有可用选项
python tests/run_tests.py --help

# 详细输出模式
python tests/run_tests.py --unit --verbose

# 运行特定测试文件
python -m unittest tests/test_client.py
python -m unittest tests.test_client.TestPLLMClient.test_generate

# 运行单个测试方法
python -m unittest tests.test_client.TestPLLMClient.test_chat

# 使用标准unittest运行器（CLAUDE.md推荐）
python -m unittest tests/test_client.py
```

## 测试覆盖范围

### Client接口覆盖
- ✅ `chat()` / `chat_sync()` - 聊天接口
- ✅ `generate()` / `generate_sync()` - 文本生成  
- ✅ `execute()` / `invoke()` / `invoke_batch()` - 调用接口
- ✅ `embedding()` / `embedding_sync()` - 向量化
- ✅ `get_stats()` - 统计信息

### Provider功能覆盖  
- ✅ 基础聊天功能
- ✅ Embedding功能（支持的提供商）
- ✅ 参数传递（temperature, max_tokens等）
- ✅ 错误处理和重试
- ✅ 统计信息收集

### 系统功能覆盖
- ✅ 负载均衡算法
- ✅ 故障转移机制
- ✅ 速率限制控制
- ✅ 健康检查系统
- ✅ 并发请求处理

## 常见问题解决

### 测试失败常见原因

**1. 模块导入错误**
```bash
# 错误：ModuleNotFoundError: No module named 'pllm'
# 解决：确保项目已正确安装
pip install -e .
```

**2. API密钥相关错误**
```bash
# 错误：集成测试跳过或失败
# 解决：设置正确的环境变量
export SILICONFLOW_API_KEY="your-real-api-key"
```

**3. 异步测试错误**
```bash
# 错误：RuntimeError: cannot be called from a running event loop
# 解决：使用正确的异步测试基类（代码中已处理）
```

**4. 临时文件清理问题**
```bash
# 如果遇到权限或文件锁定问题，检查临时目录
# 测试会自动清理，但可以手动清理 /tmp/test_* 目录
```

### 调试技巧

```bash
# 1. 启用详细日志
python -m unittest tests.test_client.TestPLLMClient.test_generate -v

# 2. 查看具体错误堆栈
python -m unittest tests/test_client.py 2>&1 | head -50

# 3. 运行单个测试类
python -m unittest tests.test_client.TestPLLMClient

# 4. 使用Python调试器
python -m pdb -m unittest tests.test_client.TestPLLMClient.test_generate
```

## 注意事项

### API密钥管理
- **单元测试**：不需要真实密钥，使用Mock响应
- **集成测试**：需要设置 `SILICONFLOW_API_KEY` 环境变量  
- **其他提供商**：目前主要用Mock密钥进行测试
- **安全提醒**：永远不要将真实API密钥提交到代码仓库

### 测试隔离和性能
- 每个测试类使用独立的临时配置文件
- 异步测试使用 `IsolatedAsyncioTestCase` 确保隔离
- 健康检查任务在测试结束时会正确清理
- 单元测试速度很快，集成测试较慢（涉及真实API调用）

### 开发最佳实践
- **开发新功能时**：先写/运行相关单元测试
- **修复Bug时**：运行对应的测试确保修复有效
- **发布前**：运行完整测试套件确保无回归
- **CI/CD集成**：主要依赖单元测试，集成测试可选

## 持续集成

测试架构支持CI/CD集成：

```yaml
# GitHub Actions 示例
- name: Run Unit Tests
  run: python tests/run_tests.py --unit

- name: Run Integration Tests  
  env:
    SILICONFLOW_API_KEY: ${{ secrets.SILICONFLOW_API_KEY }}
  run: python tests/run_tests.py --integration
```

## 扩展测试

### 添加新提供商测试
1. 继承 `BaseProviderTest` 
2. 实现必要的抽象方法
3. 添加到测试运行脚本中

### 添加新功能测试
1. 在相应的测试文件中添加测试方法
2. 使用统一的Mock工具
3. 确保测试隔离和清理

这个测试架构确保了代码质量和系统可靠性，支持快速迭代和持续集成。