"""
Test script to verify retry logic implementation.
"""
import logging
from unittest.mock import Mock, patch
from agents.bedrock_client import BedrockClient, BedrockMode, BedrockAPIError

# Set up logging to see the retry messages
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

def test_retry_with_mock_throttling():
    """Test that retry logic works with throttling errors."""
    print("\n=== Testing Retry Logic with Throttling ===")
    
    with patch('agents.bedrock_client.boto3') as mock_boto3, \
         patch('agents.bedrock_client.BOTO3_AVAILABLE', True):
        # Import ClientError for mocking
        try:
            from botocore.exceptions import ClientError
        except ImportError:
            print("botocore not installed, creating mock ClientError")
            # Create a mock ClientError class
            class ClientError(Exception):
                def __init__(self, error_response, operation_name):
                    self.response = error_response
                    super().__init__(str(error_response))
            
            # Patch it into the module
            import agents.bedrock_client
            agents.bedrock_client.ClientError = ClientError
        
        mock_runtime_client = Mock()
        
        # First 2 calls fail with throttling, 3rd succeeds
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            },
            'ResponseMetadata': {
                'RequestId': 'test-request-123'
            }
        }
        
        success_response = {
            'body': Mock(),
            'ResponseMetadata': {
                'RequestId': 'test-request-456'
            }
        }
        response_body = {
            'content': [{'text': 'Success after retry!'}],
            'stop_reason': 'end_turn',
            'usage': {'input_tokens': 10, 'output_tokens': 5}
        }
        success_response['body'].read.return_value = str(response_body).replace("'", '"').encode('utf-8')
        
        # Configure side_effect: fail twice, then succeed
        mock_runtime_client.invoke_model.side_effect = [
            ClientError(error_response, 'InvokeModel'),
            ClientError(error_response, 'InvokeModel'),
            success_response
        ]
        
        mock_boto3.client.return_value = mock_runtime_client
        
        # Create client with short retry delay for testing
        client = BedrockClient(
            mode=BedrockMode.PRODUCTION,
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            max_retries=3,
            retry_delay=0.1  # Short delay for testing
        )
        
        # This should succeed after 2 retries
        result = client.invoke_model("Test prompt")
        
        print(f"✓ Success! Got response: {result['content']}")
        print(f"✓ invoke_model was called {mock_runtime_client.invoke_model.call_count} times (2 failures + 1 success)")
        assert mock_runtime_client.invoke_model.call_count == 3
        assert result['content'] == 'Success after retry!'
        

def test_retry_exhaustion():
    """Test that all retries are exhausted and error is raised."""
    print("\n=== Testing Retry Exhaustion ===")
    
    with patch('agents.bedrock_client.boto3') as mock_boto3, \
         patch('agents.bedrock_client.BOTO3_AVAILABLE', True):
        try:
            from botocore.exceptions import ClientError
        except ImportError:
            class ClientError(Exception):
                def __init__(self, error_response, operation_name):
                    self.response = error_response
                    super().__init__(str(error_response))
            
            import agents.bedrock_client
            agents.bedrock_client.ClientError = ClientError
        
        mock_runtime_client = Mock()
        
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            },
            'ResponseMetadata': {
                'RequestId': 'test-request-789'
            }
        }
        
        # Always fail
        mock_runtime_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        mock_boto3.client.return_value = mock_runtime_client
        
        client = BedrockClient(
            mode=BedrockMode.PRODUCTION,
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            max_retries=3,
            retry_delay=0.1
        )
        
        try:
            client.invoke_model("Test prompt")
            print("✗ Should have raised BedrockAPIError")
            assert False
        except BedrockAPIError as e:
            print(f"✓ Correctly raised BedrockAPIError: {str(e)}")
            assert 'throttled' in str(e).lower()
            assert '3 retry attempts' in str(e) or '3 attempts' in str(e)
            print(f"✓ invoke_model was called {mock_runtime_client.invoke_model.call_count} times")
            assert mock_runtime_client.invoke_model.call_count == 3


def test_fallback_to_mock():
    """Test graceful degradation to mock mode."""
    print("\n=== Testing Fallback to Mock Mode ===")
    
    with patch('agents.bedrock_client.boto3') as mock_boto3, \
         patch('agents.bedrock_client.BOTO3_AVAILABLE', True):
        try:
            from botocore.exceptions import ClientError
        except ImportError:
            class ClientError(Exception):
                def __init__(self, error_response, operation_name):
                    self.response = error_response
                    super().__init__(str(error_response))
            
            import agents.bedrock_client
            agents.bedrock_client.ClientError = ClientError
        
        mock_runtime_client = Mock()
        
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate exceeded'
            },
            'ResponseMetadata': {
                'RequestId': 'test-request-999'
            }
        }
        
        mock_runtime_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        mock_boto3.client.return_value = mock_runtime_client
        
        # Enable fallback to mock
        client = BedrockClient(
            mode=BedrockMode.PRODUCTION,
            aws_access_key_id='test_key',
            aws_secret_access_key='test_secret',
            max_retries=2,
            retry_delay=0.1,
            enable_fallback_to_mock=True
        )
        
        # Should fall back to mock instead of raising error
        result = client.invoke_model("Test prompt about consumption")
        
        print(f"✓ Fell back to mock mode successfully")
        print(f"✓ Got mock response: {result['content'][:50]}...")
        assert 'Mock response' in result['content'] or 'consumption' in result['content'].lower()
        assert result['stop_reason'] == 'end_turn'


def test_mock_mode_no_retry():
    """Test that mock mode doesn't use retry logic."""
    print("\n=== Testing Mock Mode (No Retry) ===")
    
    client = BedrockClient(
        mode=BedrockMode.MOCK,
        max_retries=3,
        retry_delay=1.0
    )
    
    result = client.invoke_model("Test prompt")
    print(f"✓ Mock mode works: {result['content'][:50]}...")
    assert result['stop_reason'] == 'end_turn'


if __name__ == '__main__':
    test_mock_mode_no_retry()
    test_retry_with_mock_throttling()
    test_retry_exhaustion()
    test_fallback_to_mock()
    print("\n=== All Tests Passed! ===")
