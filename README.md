# Parallel LLM Client Framework

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

A parallel Large Language Model invocation framework providing:
- Load balancing across multiple LLM providers
- Hybrid synchronous/asynchronous interfaces
- Automatic failover and intelligent retry mechanisms
- Performance benchmarking utilities

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Usage

Config

```python
from pllm.client import LLMClient
```

