"""
Tests for AWS Bedrock client.

Tests cover:
- Client initialization in production and mock modes
- AWS credential configuration
- Connection testing
- Model invocation
- Error handling
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from agents.bedrock_client import (
    BedrockClient,
    BedrockMode,
    BedrockClientError,
    BedrockConnectionError,
    BedrockAuthenticationError,
    BedrockAPIError,
    create_bedrock_client
)


# ============================================================================
# Mock Mode Tests
# ============================================================================

def test_mock_client_initialization():
    """Test that mock client initializes without AWS credentials."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    assert client.mode == BedrockMode.MOCK
    assert client.model_id == BedrockClient.DEFAULT_MODEL_ID
    assert client._bedrock_runtime is None


def test_mock_client_test_connection():
    """Test that mock client connection test always succeeds."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    result = client.test_connection()
    assert result is True


def test_mock_client_invoke_model():
    """Test that mock client returns simulated responses."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    response = client.invoke_model("Analyze consumption data")
    
    assert 'content' in response
    assert 'stop_reason' in response
    assert 'usage' in response
    assert response['stop_reason'] == 'end_turn'
    assert len(response['content']) > 0


def test_mock_client_multiple_invocations():
    """Test that mock client handles multiple invocations."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    response1 = client.invoke_model("First prompt")
    response2 = client.invoke_model("Second prompt")
    
    assert response1['content'] != response2['content']
    assert client._mock_response_count == 2


def test_mock_client_contextual_responses():
    """Test that mock client provides contextual responses based on prompt."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    # Test consumption-related prompt
    response = client.invoke_model("Analyze the consumption data")
    assert 'consumption' in response['content'].lower()
    
    # Test emissions-related prompt
    response = client.invoke_model("Calculate emissions")
    assert 'emissions' in response['content'].lower()
    
    # Test error-related prompt
    response = client.invoke_model("What's the error?")
    assert 'error' in response['content'].lower() or 'issue' in response['content'].lower()


def test_mock_client_get_info():
    """Test that mock client returns correct configuration info."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    info = client.get_client_info()
    
    assert info['mode'] == 'mock'
    assert info['model_id'] == BedrockClient.DEFAULT_MODEL_ID
    assert info['credentials_configured'] is True
    assert info['client_initialized'] is True


# ============================================================================
# Production Mode Tests (with mocking)
# ============================================================================

@patch('agents.bedrock_client.BOTO3_AVAILABLE', True)
@patch('agents.bedrock_client.boto3')
def test_production_client_initialization_with_credentials(mock_boto3):
    """Test production client initialization with explicit credentials."""
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret',
        region='us-west-2'
    )
    
    assert client.mode == BedrockMode.PRODUCTION
    assert client.region == 'us-west-2'
    assert client._bedrock_runtime is not None
    
    # Verify boto3 client was called with correct parameters
    mock_boto3.client.assert_called_once()
    call_kwargs = mock_boto3.client.call_args[1]
    assert call_kwargs['service_name'] == 'bedrock-runtime'
    assert call_kwargs['region_name'] == 'us-west-2'
    assert call_kwargs['aws_access_key_id'] == 'test_key'
    assert call_kwargs['aws_secret_access_key'] == 'test_secret'


@patch('agents.bedrock_client.BOTO3_AVAILABLE', True)
@patch('agents.bedrock_client.boto3')
def test_production_client_initialization_with_session_token(mock_boto3):
    """Test production client initialization with temporary credentials."""
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret',
        aws_session_token='test_token'
    )
    
    # Verify session token was passed
    call_kwargs = mock_boto3.client.call_args[1]
    assert call_kwargs['aws_session_token'] == 'test_token'


@patch('agents.bedrock_client.BOTO3_AVAILABLE', True)
@patch('agents.bedrock_client.boto3')
def test_production_client_initialization_without_explicit_credentials(mock_boto3):
    """Test production client initialization using environment/IAM credentials."""
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    client = BedrockClient(mode=BedrockMode.PRODUCTION)
    
    # Verify boto3 client was called without explicit credentials
    call_kwargs = mock_boto3.client.call_args[1]
    assert 'aws_access_key_id' not in call_kwargs
    assert 'aws_secret_access_key' not in call_kwargs


@patch('agents.bedrock_client.BOTO3_AVAILABLE', True)
@patch('agents.bedrock_client.NoCredentialsError', Exception)
@patch('agents.bedrock_client.boto3')
def test_production_client_no_credentials_error(mock_boto3):
    """Test that missing credentials raise appropriate error."""
    from agents.bedrock_client import NoCredentialsError as MockNoCredentialsError
    
    mock_boto3.client.side_effect = MockNoCredentialsError()
    
    with pytest.raises(BedrockAuthenticationError) as exc_info:
        BedrockClient(mode=BedrockMode.PRODUCTION)
    
    assert 'credentials not found' in str(exc_info.value).lower()


def test_production_client_boto3_not_installed():
    """Test error when boto3 is not installed."""
    with patch('agents.bedrock_client.BOTO3_AVAILABLE', False):
        with pytest.raises(BedrockConnectionError) as exc_info:
            BedrockClient(mode=BedrockMode.PRODUCTION)
        
        assert 'boto3 is not installed' in str(exc_info.value).lower()


@patch('agents.bedrock_client.BOTO3_AVAILABLE', True)
@patch('agents.bedrock_client.boto3')
def test_production_client_custom_model_id(mock_boto3):
    """Test production client with custom model ID."""
    mock_client = Mock()
    mock_boto3.client.return_value = mock_client
    
    custom_model = "anthropic.claude-3-opus-20240229-v1:0"
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        model_id=custom_model,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    assert client.model_id == custom_model


# ============================================================================
# Connection Testing
# ============================================================================

@patch('agents.bedrock_client.boto3')
def test_production_test_connection_success(mock_boto3):
    """Test successful connection test in production mode."""
    # Mock bedrock-runtime client
    mock_runtime_client = Mock()
    
    # Mock bedrock client for connection test
    mock_bedrock_client = Mock()
    mock_bedrock_client.list_foundation_models.return_value = {
        'modelSummaries': [
            {'modelId': BedrockClient.DEFAULT_MODEL_ID}
        ]
    }
    
    def client_factory(*args, **kwargs):
        if kwargs.get('service_name') == 'bedrock-runtime':
            return mock_runtime_client
        else:
            return mock_bedrock_client
    
    mock_boto3.client.side_effect = client_factory
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    result = client.test_connection()
    assert result is True


@patch('agents.bedrock_client.boto3')
def test_production_test_connection_access_denied(mock_boto3):
    """Test connection test with access denied error."""
    from botocore.exceptions import ClientError
    
    mock_runtime_client = Mock()
    mock_bedrock_client = Mock()
    
    error_response = {
        'Error': {
            'Code': 'AccessDeniedException',
            'Message': 'Access denied'
        }
    }
    mock_bedrock_client.list_foundation_models.side_effect = ClientError(
        error_response, 'ListFoundationModels'
    )
    
    def client_factory(*args, **kwargs):
        if kwargs.get('service_name') == 'bedrock-runtime':
            return mock_runtime_client
        else:
            return mock_bedrock_client
    
    mock_boto3.client.side_effect = client_factory
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    with pytest.raises(BedrockConnectionError) as exc_info:
        client.test_connection()
    
    assert 'access denied' in str(exc_info.value).lower()


@patch('agents.bedrock_client.boto3')
def test_production_test_connection_invalid_credentials(mock_boto3):
    """Test connection test with invalid credentials."""
    from botocore.exceptions import ClientError
    
    mock_runtime_client = Mock()
    mock_bedrock_client = Mock()
    
    error_response = {
        'Error': {
            'Code': 'UnrecognizedClientException',
            'Message': 'Invalid credentials'
        }
    }
    mock_bedrock_client.list_foundation_models.side_effect = ClientError(
        error_response, 'ListFoundationModels'
    )
    
    def client_factory(*args, **kwargs):
        if kwargs.get('service_name') == 'bedrock-runtime':
            return mock_runtime_client
        else:
            return mock_bedrock_client
    
    mock_boto3.client.side_effect = client_factory
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    with pytest.raises(BedrockAuthenticationError) as exc_info:
        client.test_connection()
    
    assert 'invalid' in str(exc_info.value).lower()


# ============================================================================
# Model Invocation Tests
# ============================================================================

@patch('agents.bedrock_client.boto3')
def test_production_invoke_model_success(mock_boto3):
    """Test successful model invocation in production mode."""
    mock_runtime_client = Mock()
    
    # Mock successful response
    mock_response = {
        'body': Mock()
    }
    response_body = {
        'content': [{'text': 'This is a test response'}],
        'stop_reason': 'end_turn',
        'usage': {'input_tokens': 10, 'output_tokens': 5}
    }
    mock_response['body'].read.return_value = bytes(
        str(response_body).replace("'", '"'), 'utf-8'
    )
    mock_runtime_client.invoke_model.return_value = mock_response
    
    mock_boto3.client.return_value = mock_runtime_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    result = client.invoke_model("Test prompt")
    
    assert result['content'] == 'This is a test response'
    assert result['stop_reason'] == 'end_turn'
    assert 'usage' in result


@patch('agents.bedrock_client.boto3')
def test_production_invoke_model_with_system_prompt(mock_boto3):
    """Test model invocation with system prompt."""
    mock_runtime_client = Mock()
    
    mock_response = {
        'body': Mock()
    }
    response_body = {
        'content': [{'text': 'Response'}],
        'stop_reason': 'end_turn',
        'usage': {}
    }
    mock_response['body'].read.return_value = bytes(
        str(response_body).replace("'", '"'), 'utf-8'
    )
    mock_runtime_client.invoke_model.return_value = mock_response
    
    mock_boto3.client.return_value = mock_runtime_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    result = client.invoke_model(
        "Test prompt",
        system_prompt="You are an emissions analysis expert"
    )
    
    # Verify system prompt was included in request
    call_args = mock_runtime_client.invoke_model.call_args
    import json
    request_body = json.loads(call_args[1]['body'])
    assert 'system' in request_body
    assert request_body['system'] == "You are an emissions analysis expert"


@patch('agents.bedrock_client.boto3')
def test_production_invoke_model_throttling_error(mock_boto3):
    """Test handling of API throttling error."""
    from botocore.exceptions import ClientError
    
    mock_runtime_client = Mock()
    
    error_response = {
        'Error': {
            'Code': 'ThrottlingException',
            'Message': 'Rate exceeded'
        }
    }
    mock_runtime_client.invoke_model.side_effect = ClientError(
        error_response, 'InvokeModel'
    )
    
    mock_boto3.client.return_value = mock_runtime_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    with pytest.raises(BedrockAPIError) as exc_info:
        client.invoke_model("Test prompt")
    
    assert 'throttled' in str(exc_info.value).lower()


@patch('agents.bedrock_client.boto3')
def test_production_invoke_model_validation_error(mock_boto3):
    """Test handling of validation error."""
    from botocore.exceptions import ClientError
    
    mock_runtime_client = Mock()
    
    error_response = {
        'Error': {
            'Code': 'ValidationException',
            'Message': 'Invalid parameters'
        }
    }
    mock_runtime_client.invoke_model.side_effect = ClientError(
        error_response, 'InvokeModel'
    )
    
    mock_boto3.client.return_value = mock_runtime_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    with pytest.raises(BedrockAPIError) as exc_info:
        client.invoke_model("Test prompt")
    
    assert 'invalid request' in str(exc_info.value).lower()


# ============================================================================
# Factory Function Tests
# ============================================================================

def test_create_bedrock_client_default():
    """Test factory function with default settings."""
    with patch.dict(os.environ, {'BEDROCK_MODE': 'mock'}):
        client = create_bedrock_client()
        
        assert client.mode == BedrockMode.MOCK


def test_create_bedrock_client_explicit_mode():
    """Test factory function with explicit mode."""
    client = create_bedrock_client(mode='mock')
    
    assert client.mode == BedrockMode.MOCK


def test_create_bedrock_client_from_environment():
    """Test factory function reads configuration from environment."""
    with patch.dict(os.environ, {
        'BEDROCK_MODE': 'mock',
        'BEDROCK_MODEL_ID': 'custom-model',
        'AWS_REGION': 'eu-west-1'
    }):
        client = create_bedrock_client()
        
        assert client.mode == BedrockMode.MOCK
        assert client.model_id == 'custom-model'
        assert client.region == 'eu-west-1'


@patch('agents.bedrock_client.boto3')
def test_create_bedrock_client_production_mode(mock_boto3):
    """Test factory function creates production client."""
    mock_boto3.client.return_value = Mock()
    
    with patch.dict(os.environ, {'BEDROCK_MODE': 'production'}):
        client = create_bedrock_client(
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret'
        )
        
        assert client.mode == BedrockMode.PRODUCTION


# ============================================================================
# Client Info Tests
# ============================================================================

def test_get_client_info_mock():
    """Test client info for mock mode."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    info = client.get_client_info()
    
    assert info['mode'] == 'mock'
    assert info['credentials_configured'] is True
    assert info['client_initialized'] is True


@patch('agents.bedrock_client.boto3')
def test_get_client_info_production(mock_boto3):
    """Test client info for production mode."""
    mock_boto3.client.return_value = Mock()
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    info = client.get_client_info()
    
    assert info['mode'] == 'production'
    assert info['credentials_configured'] is True
    assert info['client_initialized'] is True


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_mock_client_with_custom_parameters():
    """Test mock client accepts but ignores custom parameters."""
    client = BedrockClient(
        mode=BedrockMode.MOCK,
        model_id='custom-model',
        region='custom-region',
        aws_access_key_id='ignored',
        aws_secret_access_key='ignored'
    )
    
    assert client.model_id == 'custom-model'
    assert client.region == 'custom-region'
    # Mock mode should still work
    assert client.test_connection() is True


def test_mock_invoke_with_custom_parameters():
    """Test mock invocation with custom parameters."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    response = client.invoke_model(
        "Test prompt",
        max_tokens=1000,
        temperature=0.5,
        top_p=0.8,
        system_prompt="Custom system"
    )
    
    assert 'content' in response
    assert len(response['content']) > 0


@patch('agents.bedrock_client.boto3')
def test_production_invoke_model_empty_response(mock_boto3):
    """Test handling of empty model response."""
    mock_runtime_client = Mock()
    
    mock_response = {
        'body': Mock()
    }
    response_body = {
        'content': [],
        'stop_reason': 'end_turn',
        'usage': {}
    }
    mock_response['body'].read.return_value = bytes(
        str(response_body).replace("'", '"'), 'utf-8'
    )
    mock_runtime_client.invoke_model.return_value = mock_response
    
    mock_boto3.client.return_value = mock_runtime_client
    
    client = BedrockClient(
        mode=BedrockMode.PRODUCTION,
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret'
    )
    
    result = client.invoke_model("Test prompt")
    
    assert result['content'] == ''
    assert result['stop_reason'] == 'end_turn'
