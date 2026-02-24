# AWS Bedrock Client for Emissions Intelligence Agent

This module provides a client for interacting with AWS Bedrock's Claude 3 model, with support for both production mode (real Bedrock API) and mock mode (for development/testing).

## Features

- **Production Mode**: Connects to AWS Bedrock with Claude 3 for real AI-powered analysis
- **Mock Mode**: Simulates Bedrock responses for development and testing without AWS credentials
- **Flexible Credentials**: Supports environment variables, IAM roles, and explicit credentials
- **Connection Testing**: Verify Bedrock access before making API calls
- **Error Handling**: Graceful handling of authentication, connection, and API errors
- **Configurable**: Custom model IDs, regions, and parameters

## Installation

```bash
pip install boto3
```

## Quick Start

### Mock Mode (No AWS Credentials Required)

```python
from agents.bedrock_client import BedrockClient, BedrockMode

# Create client in mock mode
client = BedrockClient(mode=BedrockMode.MOCK)

# Test connection
assert client.test_connection()

# Invoke model
response = client.invoke_model(
    "Analyze the consumption data and identify patterns",
    system_prompt="You are an emissions analysis expert"
)

print(response['content'])
```

### Production Mode with Environment Credentials

```python
import os
from agents.bedrock_client import create_bedrock_client

# Set environment variables
os.environ['AWS_ACCESS_KEY_ID'] = 'your-access-key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'your-secret-key'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['BEDROCK_MODE'] = 'production'

# Create client from environment
client = create_bedrock_client()

# Test connection
try:
    client.test_connection()
    print("Connected to Bedrock successfully!")
except Exception as e:
    print(f"Connection failed: {e}")

# Invoke model
response = client.invoke_model("Analyze this emissions data")
print(response['content'])
```

### Production Mode with Explicit Credentials

```python
from agents.bedrock_client import BedrockClient, BedrockMode

client = BedrockClient(
    mode=BedrockMode.PRODUCTION,
    aws_access_key_id='your-access-key',
    aws_secret_access_key='your-secret-key',
    region='us-east-1'
)

response = client.invoke_model("Calculate emissions")
```

### Production Mode with IAM Role (EC2/ECS/Lambda)

```python
from agents.bedrock_client import BedrockClient, BedrockMode

# No credentials needed - uses IAM role attached to instance
client = BedrockClient(mode=BedrockMode.PRODUCTION)

response = client.invoke_model("Analyze emissions patterns")
```

## Configuration

### Environment Variables

- `BEDROCK_MODE`: Operating mode (`production` or `mock`)
- `BEDROCK_MODEL_ID`: Claude 3 model identifier (default: `anthropic.claude-3-sonnet-20240229-v1:0`)
- `AWS_REGION`: AWS region (default: `us-east-1`)
- `AWS_ACCESS_KEY_ID`: AWS access key (optional)
- `AWS_SECRET_ACCESS_KEY`: AWS secret key (optional)

### Model IDs

Available Claude 3 models:
- `anthropic.claude-3-sonnet-20240229-v1:0` (default, balanced performance)
- `anthropic.claude-3-opus-20240229-v1:0` (most capable, higher cost)
- `anthropic.claude-3-haiku-20240307-v1:0` (fastest, lower cost)

## API Reference

### BedrockClient

#### Constructor

```python
BedrockClient(
    mode: BedrockMode = BedrockMode.PRODUCTION,
    model_id: Optional[str] = None,
    region: Optional[str] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_session_token: Optional[str] = None
)
```

#### Methods

**`test_connection() -> bool`**

Test connection to Bedrock service. Returns `True` if successful.

```python
if client.test_connection():
    print("Bedrock is accessible")
```

**`invoke_model(prompt, max_tokens=4096, temperature=0.7, top_p=0.9, system_prompt=None) -> Dict`**

Invoke Claude 3 model with a prompt.

Parameters:
- `prompt` (str): User prompt/question
- `max_tokens` (int): Maximum tokens in response (default: 4096)
- `temperature` (float): Sampling temperature 0.0-1.0 (default: 0.7)
- `top_p` (float): Nucleus sampling parameter (default: 0.9)
- `system_prompt` (str, optional): System prompt for context

Returns:
- Dictionary with keys: `content`, `stop_reason`, `usage`

```python
response = client.invoke_model(
    "Analyze emissions data",
    max_tokens=2000,
    temperature=0.5,
    system_prompt="You are an emissions expert"
)

print(response['content'])
print(f"Tokens used: {response['usage']}")
```

**`get_client_info() -> Dict`**

Get information about client configuration.

```python
info = client.get_client_info()
print(f"Mode: {info['mode']}")
print(f"Model: {info['model_id']}")
print(f"Region: {info['region']}")
```

### Factory Function

**`create_bedrock_client(mode=None, **kwargs) -> BedrockClient`**

Create a BedrockClient with configuration from environment.

```python
# Reads BEDROCK_MODE, AWS_REGION, etc. from environment
client = create_bedrock_client()

# Override mode
client = create_bedrock_client(mode='mock')

# Pass additional parameters
client = create_bedrock_client(
    mode='production',
    model_id='anthropic.claude-3-opus-20240229-v1:0'
)
```

## Error Handling

### Exception Types

- `BedrockClientError`: Base exception for all Bedrock client errors
- `BedrockConnectionError`: Connection to Bedrock failed
- `BedrockAuthenticationError`: AWS credentials missing or invalid
- `BedrockAPIError`: Bedrock API returned an error

### Example

```python
from agents.bedrock_client import (
    BedrockClient,
    BedrockConnectionError,
    BedrockAuthenticationError,
    BedrockAPIError
)

try:
    client = BedrockClient(mode=BedrockMode.PRODUCTION)
    client.test_connection()
    response = client.invoke_model("Analyze data")
    
except BedrockAuthenticationError as e:
    print(f"Authentication failed: {e}")
    print("Check your AWS credentials")
    
except BedrockConnectionError as e:
    print(f"Connection failed: {e}")
    print("Check your network and IAM permissions")
    
except BedrockAPIError as e:
    print(f"API error: {e}")
    if "throttled" in str(e).lower():
        print("Rate limit exceeded, retry later")
```

## AWS Setup

### Prerequisites

1. **AWS Account**: Sign up at https://aws.amazon.com
2. **Bedrock Access**: Request access to Claude 3 models in AWS Bedrock console
3. **IAM Permissions**: Ensure your IAM user/role has Bedrock permissions

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

### Local Development Setup

1. Install AWS CLI:
```bash
pip install awscli
```

2. Configure credentials:
```bash
aws configure
```

3. Test access:
```bash
aws bedrock list-foundation-models --region us-east-1
```

### Production Deployment

For EC2/ECS/Lambda deployments:

1. Create IAM role with Bedrock permissions
2. Attach role to your compute resource
3. Use `BedrockClient(mode=BedrockMode.PRODUCTION)` without explicit credentials

## Testing

### Run Unit Tests

```bash
pytest test_bedrock_client.py -v
```

### Run Integration Tests

```bash
pytest test_bedrock_integration.py -v
```

### Mock Mode for CI/CD

In CI/CD pipelines, use mock mode to test without AWS credentials:

```python
import os
os.environ['BEDROCK_MODE'] = 'mock'

from agents.bedrock_client import create_bedrock_client

client = create_bedrock_client()
# Tests will use mock responses
```

## Best Practices

1. **Use Mock Mode for Development**: Develop and test locally without AWS costs
2. **Environment Variables**: Store credentials in environment, not code
3. **IAM Roles for Production**: Use IAM roles instead of access keys in production
4. **Error Handling**: Always wrap Bedrock calls in try/except blocks
5. **Connection Testing**: Test connection before making multiple API calls
6. **Cost Monitoring**: Monitor Bedrock usage in AWS Cost Explorer

## Troubleshooting

### "boto3 is not installed"

```bash
pip install boto3
```

### "AWS credentials not found"

Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

Or configure AWS CLI:
```bash
aws configure
```

### "Access denied to Bedrock service"

1. Check IAM permissions include `bedrock:InvokeModel`
2. Verify Bedrock is available in your region
3. Request model access in Bedrock console

### "Model not found"

1. Verify model ID is correct
2. Check if model is available in your region
3. Request access to specific model in Bedrock console

## Examples

### Emissions Analysis Workflow

```python
from agents.bedrock_client import create_bedrock_client

# Initialize client
client = create_bedrock_client()

# Step 1: Analyze data structure
response = client.invoke_model(
    "I have consumption data with timestamps. What should I check?",
    system_prompt="You are an emissions analysis expert"
)
print("Analysis:", response['content'])

# Step 2: Calculate emissions
response = client.invoke_model(
    "Calculate emissions using interval-based method",
    system_prompt="You are an emissions analysis expert"
)
print("Calculation:", response['content'])

# Step 3: Generate insights
response = client.invoke_model(
    "What patterns do you see in the emissions data?",
    system_prompt="You are an emissions analysis expert"
)
print("Insights:", response['content'])
```

### Batch Processing

```python
prompts = [
    "Analyze consumption patterns",
    "Identify high-emission periods",
    "Suggest reduction strategies"
]

for prompt in prompts:
    response = client.invoke_model(prompt)
    print(f"Q: {prompt}")
    print(f"A: {response['content']}\n")
```

## License

This module is part of the Emissions Dashboard project.
