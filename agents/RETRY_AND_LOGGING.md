# Bedrock Client: Error Handling, Retry Logic, and Logging

## Overview

The Bedrock client now includes comprehensive error handling, retry logic with exponential backoff, and detailed logging capabilities. These features improve reliability and observability when interacting with AWS Bedrock's Claude 3 API.

## Features

### 1. Logging

The client uses Python's standard `logging` module with logger name `'bedrock_client'`.

#### Log Levels

- **INFO**: Normal operations (initialization, API calls, successful responses)
- **WARNING**: Retry attempts, fallback to mock mode
- **ERROR**: API failures, exhausted retries

#### What Gets Logged

**Client Initialization:**
```
INFO - Initializing BedrockClient: mode=production, model_id=anthropic.claude-3-sonnet-20240229-v1:0, 
       region=us-east-1, max_retries=3, retry_delay=1.0s, enable_fallback_to_mock=False
```

**API Calls:**
```
INFO - Invoking model: prompt_length=150 chars, max_tokens=4096, temperature=0.7, 
       top_p=0.9, system_prompt=set
```

**Successful Responses:**
```
INFO - Bedrock API call successful: request_id=abc-123, stop_reason=end_turn, 
       input_tokens=45, output_tokens=120
```

**Retry Attempts:**
```
WARNING - Bedrock API call attempt 1/3 failed with ThrottlingException (request_id=abc-123). 
          Retrying in 1.0s...
WARNING - Bedrock API call attempt 2/3 failed with ThrottlingException (request_id=abc-123). 
          Retrying in 2.0s...
```

**Failures:**
```
ERROR - Bedrock API call failed after 3 attempts with ThrottlingException (request_id=abc-123): 
        Rate exceeded
```

#### Configuring Logging

```python
import logging

# Basic configuration
logging.basicConfig(level=logging.INFO)

# More detailed configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bedrock_client.log'),
        logging.StreamHandler()
    ]
)

# Adjust log level for bedrock_client only
logger = logging.getLogger('bedrock_client')
logger.setLevel(logging.DEBUG)
```

### 2. Retry Logic with Exponential Backoff

The client automatically retries failed API calls with exponential backoff for `ThrottlingException` errors.

#### Configuration Parameters

```python
client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=3,              # Maximum retry attempts (default: 3)
    retry_delay=1.0,            # Base delay in seconds (default: 1.0)
    enable_fallback_to_mock=False  # Graceful degradation (default: False)
)
```

#### Retry Behavior

- **Retry Condition**: Only `ThrottlingException` errors trigger retries
- **Delay Calculation**: `retry_delay * (2 ** attempt)`
  - Attempt 1: 1.0s delay
  - Attempt 2: 2.0s delay
  - Attempt 3: 4.0s delay
- **Other Errors**: `ValidationException` and other errors fail immediately without retry

#### Example: Successful Retry

```python
from agents.bedrock_client import BedrockClient, BedrockMode

client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=3,
    retry_delay=1.0
)

# If throttled, will retry up to 3 times with exponential backoff
response = client.invoke_model("Analyze this emissions data")
print(response['content'])
```

**Log Output:**
```
INFO - Invoking model: prompt_length=28 chars, max_tokens=4096, temperature=0.7, top_p=0.9, system_prompt=none
WARNING - Bedrock API call attempt 1/3 failed with ThrottlingException (request_id=req-123). Retrying in 1.0s...
WARNING - Bedrock API call attempt 2/3 failed with ThrottlingException (request_id=req-123). Retrying in 2.0s...
INFO - Bedrock API call successful: request_id=req-456, stop_reason=end_turn, input_tokens=10, output_tokens=50
```

### 3. Graceful Degradation to Mock Mode

When `enable_fallback_to_mock=True`, the client falls back to mock mode if all retries are exhausted.

#### Use Cases

- **Development**: Continue working when AWS credentials are unavailable
- **Testing**: Simulate API failures without breaking the application
- **Resilience**: Provide degraded service instead of complete failure

#### Example

```python
client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=2,
    retry_delay=0.5,
    enable_fallback_to_mock=True  # Enable graceful degradation
)

# If all retries fail, falls back to mock response
response = client.invoke_model("Analyze emissions")
print(response['content'])  # Returns mock response instead of raising error
```

**Log Output:**
```
INFO - Invoking model: prompt_length=17 chars, max_tokens=4096, temperature=0.7, top_p=0.9, system_prompt=none
WARNING - Bedrock API call attempt 1/2 failed with ThrottlingException (request_id=req-789). Retrying in 0.5s...
ERROR - Bedrock API call failed after 2 attempts with ThrottlingException (request_id=req-789): Rate exceeded
WARNING - Falling back to mock mode due to repeated throttling errors
```

### 4. Request Tracking

All log messages include AWS `request_id` when available, enabling correlation with AWS CloudWatch logs.

```python
# Logs include request_id for tracking
INFO - Bedrock API call successful: request_id=abc-123-def-456, stop_reason=end_turn, ...
```

## Error Handling

### Exception Hierarchy

```
BedrockClientError (base)
├── BedrockConnectionError
├── BedrockAuthenticationError
└── BedrockAPIError
```

### Error Types

**ThrottlingException** (with retry):
```python
try:
    response = client.invoke_model("prompt")
except BedrockAPIError as e:
    # Raised after all retries exhausted
    print(f"API throttled: {e}")
```

**ValidationException** (no retry):
```python
try:
    response = client.invoke_model("prompt", max_tokens=-1)  # Invalid
except BedrockAPIError as e:
    # Raised immediately
    print(f"Invalid parameters: {e}")
```

**Other Errors** (no retry):
```python
try:
    response = client.invoke_model("prompt")
except BedrockAPIError as e:
    # Raised immediately for non-throttling errors
    print(f"API error: {e}")
```

## Best Practices

### 1. Configure Logging Early

```python
import logging

# Configure before creating client
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from agents.bedrock_client import BedrockClient, BedrockMode
client = BedrockClient(mode=BedrockMode.PRODUCTION)
```

### 2. Adjust Retry Parameters Based on Use Case

**Interactive Applications** (fast failure):
```python
client = BedrockClient(
    max_retries=2,
    retry_delay=0.5
)
```

**Batch Processing** (more resilient):
```python
client = BedrockClient(
    max_retries=5,
    retry_delay=2.0
)
```

**Development** (with fallback):
```python
client = BedrockClient(
    max_retries=1,
    retry_delay=0.5,
    enable_fallback_to_mock=True
)
```

### 3. Monitor Logs for Throttling Patterns

```python
# Set up file logging to track throttling over time
logging.basicConfig(
    level=logging.WARNING,  # Only warnings and errors
    filename='bedrock_throttling.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 4. Handle Errors Appropriately

```python
from agents.bedrock_client import BedrockClient, BedrockAPIError

client = BedrockClient(mode=BedrockMode.PRODUCTION)

try:
    response = client.invoke_model("Analyze data")
    process_response(response)
except BedrockAPIError as e:
    if 'throttled' in str(e).lower():
        # Handle throttling specifically
        logger.error("API throttled, consider reducing request rate")
    else:
        # Handle other API errors
        logger.error(f"API error: {e}")
```

## Testing

### Unit Tests

The retry logic is fully tested in `test_retry_logic.py`:

```bash
python emissions-dashboard/test_retry_logic.py
```

### Integration Tests

All existing tests maintain backward compatibility:

```bash
# Mock mode tests
pytest emissions-dashboard/test_bedrock_client.py -k "mock" -v

# Integration tests
pytest emissions-dashboard/test_bedrock_integration.py -v
```

## Backward Compatibility

All new parameters have sensible defaults, ensuring existing code continues to work:

```python
# Old code still works
client = BedrockClient(mode=BedrockMode.PRODUCTION)

# New features are opt-in
client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=5,              # Optional
    retry_delay=2.0,            # Optional
    enable_fallback_to_mock=True  # Optional
)
```

## Performance Considerations

### Retry Delays

With default settings (`max_retries=3`, `retry_delay=1.0`):
- Total retry time: 1.0s + 2.0s = 3.0s
- Maximum call duration: ~3-4 seconds (plus API response time)

### Logging Overhead

Logging has minimal performance impact:
- INFO level: ~0.1ms per log statement
- File logging: ~1-2ms per statement
- Recommendation: Use INFO level in production, DEBUG for troubleshooting

## Migration Guide

### From Previous Version

No changes required! The new features are backward compatible:

```python
# This still works exactly as before
client = BedrockClient(mode=BedrockMode.PRODUCTION)
response = client.invoke_model("prompt")
```

### Enabling New Features

```python
# Add logging
import logging
logging.basicConfig(level=logging.INFO)

# Add retry configuration
client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=3,
    retry_delay=1.0
)

# Add fallback (optional)
client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    max_retries=3,
    retry_delay=1.0,
    enable_fallback_to_mock=True
)
```

## Troubleshooting

### Issue: Too Many Retries

**Symptom**: Requests take too long
**Solution**: Reduce `max_retries` or `retry_delay`

```python
client = BedrockClient(max_retries=2, retry_delay=0.5)
```

### Issue: Not Seeing Logs

**Symptom**: No log output
**Solution**: Configure logging before creating client

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Issue: Throttling Errors

**Symptom**: Frequent `ThrottlingException`
**Solution**: 
1. Increase `retry_delay` for longer backoff
2. Reduce request rate in your application
3. Request AWS quota increase

```python
client = BedrockClient(max_retries=5, retry_delay=2.0)
```

## Summary

The enhanced Bedrock client provides:
- ✅ Comprehensive logging at all stages
- ✅ Automatic retry with exponential backoff
- ✅ Configurable retry parameters
- ✅ Graceful degradation to mock mode
- ✅ Request tracking with AWS request IDs
- ✅ Full backward compatibility
- ✅ Minimal performance overhead

These features make the client more reliable, observable, and production-ready.
