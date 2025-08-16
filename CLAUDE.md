# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation and Setup
```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run balance algorithm tests (provider selection, token counting, failover)
python3 -m unittest tests.test_balance_algorithm_mocked -v

# Run client interface tests (invoke, invoke_batch, chat, generate, etc.)
python3 -m unittest tests.test_client_interface_mocked -v

# Run output validation tests (JSON, text, regex validators)
python3 -m unittest tests.test_output_validation -v

# Run specific test methods
python3 -m unittest tests.test_balance_algorithm_mocked.TestBalanceAlgorithmMocked.test_token_counting_accuracy -v
python3 -m unittest tests.test_client_interface_mocked.TestClientInterfaceMocked.test_invoke_batch_method -v
python3 -m unittest tests.test_output_validation.TestJsonValidator.test_valid_json_object -v

# Run all unit tests (mocked)
python3 -m unittest tests.test_balance_algorithm_mocked tests.test_client_interface_mocked tests.test_output_validation -v

# Legacy manual tests (requires valid API keys)
python tests/manual_test.py
python tests/multi_key_test.py

# New organized test runner
python tests/run_tests.py --unit          # Run unit tests (mocked)
python tests/run_tests.py --validation    # Run validation tests (mocked)
python tests/run_tests.py --integration   # Run integration tests (real API)
python tests/run_tests.py --validation-integration  # Run validation with real API
python tests/run_tests.py --all          # Run all tests
```

### Usage Examples
```bash
# Run basic usage examples
python simple_usage.py
python simple_usage_embedding.py

# Run performance benchmarks
python benchmark.py
```

## Architecture Overview

### Core Components

**Client (`src/pllm/client.py`)**
- Main user interface providing both async and sync methods
- Wraps the LoadBalancer for simplified API access
- Supports: `chat()`, `generate()`, `invoke()`, `invoke_batch()`, `embedding()`
- Includes synchronous versions: `chat_sync()`, `generate_sync()`, `embedding_sync()`
- **Note**: `chat()` method now returns string content directly instead of full response dict

**LoadBalancer (`src/pllm/balancer.py`)**
- Intelligent request routing across multiple Provider instances
- Manages rate limiting, error handling, and provider health monitoring
- Uses provider-based architecture for better extensibility
- Supports retry policies: "fixed", "infinite", "retry_once"

**Provider System (`src/pllm/providers/`)**
- **BaseProvider**: Abstract base class defining provider interface
- **Supported Providers**:
  - OpenAI (chat + embedding)
  - SiliconFlow (chat + embedding) 
  - Anthropic Claude (chat only)
  - Google Gemini (chat + embedding)
  - DeepSeek (chat only)
  - Zhipu AI (chat + embedding)
- Provider registry system for easy extensibility
- Each provider handles its own API format and authentication
### Request Flow Architecture

1. **Client Interface** → User calls `client.generate()` or `client.chat()`
2. **LoadBalancer** → Selects optimal Provider based on:
   - Active request count (primary factor)
   - Error count history
   - Rate limit availability  
   - Last usage time
3. **Provider** → Executes API call via provider-specific implementation:
   - Each provider handles its own API format (OpenAI-style, Anthropic, Google, etc.)
   - Automatic request/response format conversion
   - Provider-specific authentication handling
4. **Response Processing** → Records usage statistics and returns standardized result

### Configuration System

Configurations are YAML files with structure:
```yaml
llm:
  use: "openai, anthropic, google"  # Comma-separated active providers
  openai:
    - api_key: "sk-xxx"
      api_base: "https://api.openai.com/v1"
      model: "gpt-4o-mini"
      rate_limit: 20
  anthropic:
    - api_key: "sk-ant-xxx"
      api_base: "https://api.anthropic.com"
      model: "claude-3-5-sonnet-20241022"
      rate_limit: 15
  google:
    - api_key: "your-api-key"
      api_base: "https://generativelanguage.googleapis.com"
      model: "gemini-1.5-flash"
      rate_limit: 15
```

### Error Handling & Resilience

- **Circuit Breaker Pattern**: Providers deactivated after 3 consecutive errors
- **Health Check System**: Periodic reactivation of failed providers (5-minute intervals)
- **Retry Policies**: Configurable retry behavior per request ("fixed", "infinite", "retry_once")
- **Rate Limiting**: Per-provider request throttling with sliding window
- **Load Distribution**: Smart provider selection to balance load

## Key Implementation Details

### Rate Limiting
- Uses sliding window approach with `deque(maxlen=rate_limit)`
- Checks if oldest request in queue is older than 60 seconds
- Prevents API quota exhaustion across multiple clients

### Statistics Tracking
- Per-provider metrics: `total_requests`, `total_tokens`, `error_count`
- Active request counting for accurate load balancing
- Usage statistics accessible via `client.get_stats()`
- Model information and capability tracking

### Async/Sync Hybrid Design
- Core implementation is async for performance
- Synchronous wrappers use `asyncio.run()` for compatibility
- Health check tasks handle event loop detection gracefully

### Provider Architecture Benefits
- **Decoupled Design**: Each provider is a separate class with its own logic
- **Easy Extension**: Add new providers by implementing BaseProvider interface
- **Provider Registry**: Automatic provider discovery and registration
- **Standardized Interface**: Unified API regardless of underlying provider
- **Format Handling**: Automatic conversion between provider-specific formats

## Testing Considerations

- Tests use `unittest.IsolatedAsyncioTestCase` for async support
- Mock `aiohttp.ClientSession.post` for HTTP-based provider API calls
- Temporary config files created in `asyncSetUp()`
- Health check tasks properly cancelled in `asyncTearDown()`

## Configuration Examples

See `examples/example_config.yaml` for basic two-provider setup, `examples/multi_provider_config.yaml` for comprehensive multi-provider configuration, and `examples/example_embedding_config.yaml` for embedding-specific configurations.