"""
Integration tests for Bedrock client demonstrating real-world usage.

These tests show how the Bedrock client would be used in the emissions dashboard application.
"""

import pytest
from agents.bedrock_client import (
    BedrockClient,
    BedrockMode,
    create_bedrock_client,
    BedrockConnectionError
)


def test_mock_mode_workflow():
    """Test complete workflow using mock mode."""
    # Create client in mock mode (no AWS credentials needed)
    client = create_bedrock_client(mode='mock')
    
    # Verify client is ready
    assert client.test_connection()
    
    # Get client info
    info = client.get_client_info()
    assert info['mode'] == 'mock'
    assert info['client_initialized']
    
    # Invoke model with emissions analysis prompt
    response = client.invoke_model(
        "Analyze the consumption data and identify patterns",
        system_prompt="You are an emissions analysis expert"
    )
    
    # Verify response structure
    assert 'content' in response
    assert 'stop_reason' in response
    assert 'usage' in response
    assert len(response['content']) > 0
    
    # Invoke again with different prompt (using "problem" keyword)
    response2 = client.invoke_model(
        "What is the problem with this?"
    )
    
    # Responses should be different (different keywords trigger different mock responses)
    assert 'issue' in response2['content'].lower() or 'problem' in response2['content'].lower()
    assert response2['content'] != response['content']


def test_production_mode_requires_boto3():
    """Test that production mode fails gracefully without boto3."""
    # This test verifies error handling when boto3 is not available
    # In real deployment, boto3 would be installed
    
    try:
        client = BedrockClient(mode=BedrockMode.PRODUCTION)
        # If we get here, boto3 is installed, so test connection
        # (will fail without real AWS credentials, but that's expected)
        try:
            client.test_connection()
        except Exception:
            # Expected - no real AWS credentials in test environment
            pass
    except BedrockConnectionError as e:
        # Expected when boto3 not installed
        assert 'boto3' in str(e).lower()


def test_factory_function_with_environment():
    """Test factory function respects environment configuration."""
    import os
    
    # Test with mock mode from environment
    original_mode = os.environ.get('BEDROCK_MODE')
    try:
        os.environ['BEDROCK_MODE'] = 'mock'
        client = create_bedrock_client()
        
        assert client.mode == BedrockMode.MOCK
        assert client.test_connection()
    finally:
        if original_mode:
            os.environ['BEDROCK_MODE'] = original_mode
        elif 'BEDROCK_MODE' in os.environ:
            del os.environ['BEDROCK_MODE']


def test_custom_model_configuration():
    """Test client with custom model ID."""
    custom_model = "anthropic.claude-3-opus-20240229-v1:0"
    
    client = BedrockClient(
        mode=BedrockMode.MOCK,
        model_id=custom_model,
        region='eu-west-1'
    )
    
    assert client.model_id == custom_model
    assert client.region == 'eu-west-1'
    
    # Verify it still works
    response = client.invoke_model("Test prompt")
    assert 'content' in response


def test_multiple_invocations_maintain_state():
    """Test that client maintains state across multiple invocations."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    # Make multiple calls
    responses = []
    for i in range(5):
        response = client.invoke_model(f"Prompt {i}")
        responses.append(response)
    
    # Verify all responses are valid
    assert len(responses) == 5
    for response in responses:
        assert 'content' in response
        assert len(response['content']) > 0
    
    # Verify mock counter incremented
    assert client._mock_response_count == 5


def test_error_handling_in_mock_mode():
    """Test that mock mode handles various inputs gracefully."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    # Empty prompt
    response = client.invoke_model("")
    assert 'content' in response
    
    # Very long prompt
    long_prompt = "Analyze " * 1000
    response = client.invoke_model(long_prompt)
    assert 'content' in response
    
    # Special characters
    response = client.invoke_model("Test with émissions and CO₂")
    assert 'content' in response


def test_client_info_provides_useful_debugging():
    """Test that client info helps with debugging."""
    client = BedrockClient(mode=BedrockMode.MOCK)
    
    info = client.get_client_info()
    
    # Verify all expected fields present
    assert 'mode' in info
    assert 'model_id' in info
    assert 'region' in info
    assert 'credentials_configured' in info
    assert 'client_initialized' in info
    
    # Verify values are sensible
    assert info['mode'] in ['mock', 'production']
    assert info['model_id'].startswith('anthropic.claude')
    assert len(info['region']) > 0


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
