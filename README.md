# Parallel LLM Client Framework

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

A parallel Large Language Model invocation framework providing:

- Load balancing across multiple LLM providers
- Hybrid synchronous/asynchronous interfaces
- Automatic failover and intelligent retry mechanisms

## Quick Start

### Installation

```bash
git clone https://github.com/16131zzzzzzzz/ParallelLLM.git
cd ParallelLLM
pip install -r requirements.txt
pip install -e .
```

### Configuration

1. Modify the config file: `examples/example_config.yaml`

```yaml
llm:
  use: siliconflow
  siliconflow:
    - api_key: 'sk-xxx'
      api_base: 'https://api.siliconflow.cn/v1/chat/completions'
      model: 'model name'
      rate_limit: 20

    - api_key: 'sk-xxx'
      api_base: 'https://api.siliconflow.cn/v1/chat/completions'
      model: 'model name'
      rate_limit: 20
```

### Usage Examples

#### 1. Initialize Client

```python
from pllm import Client

client = Client("examples/example_config.yaml")
```

#### 2. Common Synchronous Methods

##### 2.1 Text Generation - `invoke()` / `generate_sync()`

Generate text from a single prompt:

```python
response = client.invoke(
    "写一个快速排序算法的Python实现",
    retry_policy="retry_once",
    temperature=0.3
)
print(response)

# Alternative method (identical functionality)
response = client.generate_sync(
    "写一个正则表达式匹配邮箱地址",
    retry_policy="infinite"
)
print(response)
```

##### 2.2 Batch Processing - `invoke_batch()`

Process multiple prompts in parallel:

```python
questions = [
    "解释量子隧穿效应",
    "写一个快速排序算法",
    "什么是Transformer架构？",
    "如何用Python计算圆周率？",
    "解释深度神经网络的工作原理"
]

results = client.invoke_batch(
    questions,
    retry_policy="fixed",
    temperature=0.6
)

for i, result in enumerate(results):
    print(f"Question {i+1}: {questions[i]}")
    print(f"Answer: {result}\n")
```

##### 2.3 Text Embeddings - `embedding_sync()`

Generate text embeddings for vector similarity:

```python
embedding = client.embedding_sync(
    "计算这段文本的向量表示",
    encoding_format="float"
)
print(f"Embedding length: {len(embedding)}")
```

#### 3. Usage Statistics

Monitor API usage across all providers:

```python
stats = client.get_stats()
print("Usage Statistics:")
for provider, clients in stats.items():
    print(f"\nProvider: {provider}")
    for client_info in clients:
        print(f"  Client {client_info['id']}:")
        print(f"    Active: {client_info['active']}")
        print(f"    Total Requests: {client_info['total_requests']}")
        print(f"    Total Tokens: {client_info['total_tokens']}")
        print(f"    Error Count: {client_info['error_count']}")
```

## Advanced Usage

### Asynchronous Methods

#### Text Generation - `generate()`

```python
import asyncio

async def example_generate():
    response = await client.generate(
        "解释一下量子计算的基本原理",
        retry_policy="infinite",
        temperature=0.5
    )
    print(response)

asyncio.run(example_generate())
```

#### Text Embeddings - `embedding()`

```python
async def example_embedding():
    embedding = await client.embedding(
        "这是一段需要向量化的文本",
        encoding_format="float",
        retry_policy="fixed"
    )
    print(f"Embedding dimension: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")

asyncio.run(example_embedding())
```

### Parallel Processing

Process multiple requests simultaneously:

```python
async def parallel_processing():
    tasks = [
        client.generate("什么是机器学习？"),
        client.generate("解释深度学习原理"),
        client.generate("什么是自然语言处理？"),
        client.embedding("向量化这段文本")
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

results = asyncio.run(parallel_processing())
```

### Error Handling with Retry Policies

```python
# Infinite retry until success
response = await client.generate(
    "重要的请求，必须成功",
    retry_policy="infinite"
)

# Fixed number of retries
response = await client.generate(
    "普通请求",
    retry_policy="fixed"
)

# Only retry once
response = await client.generate(
    "简单请求",
    retry_policy="retry_once"
)
```

### Provider-Specific Requests

```python
# Force use specific provider
response = await client.generate(
    "Hello",
    provider="siliconflow"
)
```

## Test

```bash
python -m unittest tests/test_client.py
```

## TODO

- [ ] Currently only supports siliconflow, need to add more LLM providers
- [ ] Change into English comments
