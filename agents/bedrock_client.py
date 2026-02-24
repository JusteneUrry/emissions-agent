"""
AWS Bedrock client for Emissions Intelligence Agent.

This module provides a client for interacting with AWS Bedrock's Claude 3 model,
with support for both production mode (real Bedrock API) and mock mode (for testing).
"""

import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
from enum import Enum

# Import boto3 at module level for easier mocking in tests
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    NoCredentialsError = None
    ClientError = None
    BOTO3_AVAILABLE = False


class BedrockMode(Enum):
    """Operating mode for Bedrock client."""
    PRODUCTION = "production"
    MOCK = "mock"


class BedrockClientError(Exception):
    """Base exception for Bedrock client errors."""
    pass


class BedrockConnectionError(BedrockClientError):
    """Raised when connection to Bedrock fails."""
    pass


class BedrockAuthenticationError(BedrockClientError):
    """Raised when AWS credentials are missing or invalid."""
    pass


class BedrockAPIError(BedrockClientError):
    """Raised when Bedrock API returns an error."""
    pass


class BedrockClient:
    """
    Client for AWS Bedrock with Claude 3 model access.
    
    Supports both production mode (real AWS Bedrock) and mock mode (for development/testing).
    Handles AWS credential configuration, connection testing, and error handling.
    
    Attributes:
        mode: Operating mode (PRODUCTION or MOCK)
        model_id: Claude 3 model identifier
        region: AWS region for Bedrock service
        
    Example:
        >>> # Production mode with environment credentials
        >>> client = BedrockClient(mode=BedrockMode.PRODUCTION)
        >>> client.test_connection()
        True
        
        >>> # Mock mode for testing
        >>> client = BedrockClient(mode=BedrockMode.MOCK)
        >>> response = client.invoke_model("Analyze this data")
    """
    
    # Default Claude 3 model ID
    DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    DEFAULT_REGION = "us-east-1"
    
    # Set up logger
    logger = logging.getLogger('bedrock_client')
    
    def __init__(
        self,
        mode: BedrockMode = BedrockMode.PRODUCTION,
        model_id: Optional[str] = None,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_fallback_to_mock: bool = False
    ):
        """
        Initialize Bedrock client.
        
        Args:
            mode: Operating mode (PRODUCTION or MOCK)
            model_id: Claude 3 model identifier (defaults to Sonnet)
            region: AWS region (defaults to us-east-1)
            aws_access_key_id: AWS access key (optional, uses environment if not provided)
            aws_secret_access_key: AWS secret key (optional, uses environment if not provided)
            aws_session_token: AWS session token (optional, for temporary credentials)
            max_retries: Maximum number of retry attempts for throttled requests (default: 3)
            retry_delay: Base delay in seconds for exponential backoff (default: 1.0)
            enable_fallback_to_mock: Enable graceful degradation to mock mode on failure (default: False)
            
        Raises:
            BedrockAuthenticationError: If credentials are missing in production mode
            BedrockConnectionError: If unable to initialize Bedrock client
        """
        self.mode = mode
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.region = region or os.environ.get('AWS_REGION', self.DEFAULT_REGION)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_fallback_to_mock = enable_fallback_to_mock
        
        # Store credentials
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        
        # Log client initialization
        self.logger.info(
            f"Initializing BedrockClient: mode={mode.value}, model_id={self.model_id}, "
            f"region={self.region}, max_retries={max_retries}, retry_delay={retry_delay}s, "
            f"enable_fallback_to_mock={enable_fallback_to_mock}"
        )
        
        # Initialize client based on mode
        self._bedrock_runtime = None
        if mode == BedrockMode.PRODUCTION:
            self._initialize_production_client()
        else:
            self._initialize_mock_client()
    
    def _initialize_production_client(self) -> None:
        """
        Initialize production Bedrock client with boto3.
        
        Attempts to configure AWS credentials from:
        1. Explicit parameters passed to __init__
        2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        3. IAM role (for EC2/ECS/Lambda)
        4. AWS credentials file (~/.aws/credentials)
        
        Raises:
            BedrockAuthenticationError: If credentials cannot be found
            BedrockConnectionError: If boto3 import fails or client initialization fails
        """
        if not BOTO3_AVAILABLE:
            raise BedrockConnectionError(
                "boto3 is not installed. Install it with: pip install boto3"
            )
        
        try:
            # Build kwargs for boto3 client
            client_kwargs = {
                'service_name': 'bedrock-runtime',
                'region_name': self.region
            }
            
            # Add explicit credentials if provided
            if self._aws_access_key_id and self._aws_secret_access_key:
                client_kwargs['aws_access_key_id'] = self._aws_access_key_id
                client_kwargs['aws_secret_access_key'] = self._aws_secret_access_key
                if self._aws_session_token:
                    client_kwargs['aws_session_token'] = self._aws_session_token
            
            # Initialize Bedrock runtime client
            self._bedrock_runtime = boto3.client(**client_kwargs)
            
            # Initialize mock response count for fallback mode
            self._mock_response_count = 0
            
        except NoCredentialsError as e:
            raise BedrockAuthenticationError(
                "AWS credentials not found. Configure credentials via:\n"
                "1. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY\n"
                "2. AWS credentials file: ~/.aws/credentials\n"
                "3. IAM role (for EC2/ECS/Lambda)\n"
                "4. Pass credentials explicitly to BedrockClient()"
            ) from e
        except Exception as e:
            raise BedrockConnectionError(
                f"Failed to initialize Bedrock client: {str(e)}"
            ) from e
    
    def _initialize_mock_client(self) -> None:
        """
        Initialize mock client for development/testing.
        
        Mock client simulates Bedrock responses without making real API calls.
        """
        self._bedrock_runtime = None  # No real client in mock mode
        self._mock_response_count = 0
    
    def test_connection(self) -> bool:
        """
        Test connection to Bedrock service.
        
        In production mode, attempts to list available foundation models.
        In mock mode, always returns True.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            BedrockAuthenticationError: If credentials are invalid
            BedrockConnectionError: If connection fails
        """
        if self.mode == BedrockMode.MOCK:
            return True
        
        try:
            # Try to list foundation models as a connection test
            bedrock_client = boto3.client(
                'bedrock',
                region_name=self.region,
                aws_access_key_id=self._aws_access_key_id,
                aws_secret_access_key=self._aws_secret_access_key,
                aws_session_token=self._aws_session_token
            )
            
            # List models to verify access
            response = bedrock_client.list_foundation_models()
            
            # Check if our model is available
            available_models = [model['modelId'] for model in response.get('modelSummaries', [])]
            if self.model_id not in available_models:
                # Model might still be accessible even if not in list (due to permissions)
                # So we don't fail here, just log a warning
                pass
            
            return True
            
        except NoCredentialsError as e:
            raise BedrockAuthenticationError(
                "AWS credentials not found or invalid"
            ) from e
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ['UnrecognizedClientException', 'InvalidSignatureException']:
                raise BedrockAuthenticationError(
                    f"AWS credentials are invalid: {str(e)}"
                ) from e
            elif error_code == 'AccessDeniedException':
                raise BedrockConnectionError(
                    "Access denied to Bedrock service. Check IAM permissions."
                ) from e
            else:
                raise BedrockConnectionError(
                    f"Failed to connect to Bedrock: {str(e)}"
                ) from e
        except Exception as e:
            raise BedrockConnectionError(
                f"Unexpected error testing Bedrock connection: {str(e)}"
            ) from e
    
    def invoke_model(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke Claude 3 model with a prompt.
        
        Args:
            prompt: User prompt/question
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            system_prompt: Optional system prompt for context
            
        Returns:
            Dictionary with keys:
            - 'content': Generated text response
            - 'stop_reason': Reason for completion (e.g., 'end_turn', 'max_tokens')
            - 'usage': Token usage statistics
            
        Raises:
            BedrockAPIError: If API call fails
        """
        # Log the invoke_model call
        self.logger.info(
            f"Invoking model: prompt_length={len(prompt)} chars, max_tokens={max_tokens}, "
            f"temperature={temperature}, top_p={top_p}, system_prompt={'set' if system_prompt else 'none'}"
        )
        
        # Use retry logic for production mode
        return self.invoke_model_with_retry(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            system_prompt=system_prompt
        )
    
    def invoke_model_with_retry(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke Claude 3 model with retry logic for throttling errors.
        
        Implements exponential backoff retry logic for ThrottlingException.
        Optionally falls back to mock mode if all retries fail and enable_fallback_to_mock is True.
        
        Args:
            prompt: User prompt/question
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            system_prompt: Optional system prompt for context
            
        Returns:
            Dictionary with keys:
            - 'content': Generated text response
            - 'stop_reason': Reason for completion (e.g., 'end_turn', 'max_tokens')
            - 'usage': Token usage statistics
            
        Raises:
            BedrockAPIError: If API call fails after all retries
        """
        if self.mode == BedrockMode.MOCK:
            return self._mock_invoke_model(prompt, system_prompt)
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Build request body for Claude 3
                request_body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                # Add system prompt if provided
                if system_prompt:
                    request_body["system"] = system_prompt
                
                # Invoke model
                response = self._bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                
                # Extract request_id if available
                request_id = response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
                
                # Extract content
                content = ""
                if 'content' in response_body and len(response_body['content']) > 0:
                    content = response_body['content'][0].get('text', '')
                
                # Log successful response
                usage = response_body.get('usage', {})
                stop_reason = response_body.get('stop_reason', 'unknown')
                self.logger.info(
                    f"Bedrock API call successful: request_id={request_id}, "
                    f"stop_reason={stop_reason}, input_tokens={usage.get('input_tokens', 0)}, "
                    f"output_tokens={usage.get('output_tokens', 0)}"
                )
                
                return {
                    'content': content,
                    'stop_reason': stop_reason,
                    'usage': usage
                }
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                error_message = e.response.get('Error', {}).get('Message', str(e))
                request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
                
                if error_code == 'ThrottlingException':
                    last_error = e
                    
                    if attempt < self.max_retries - 1:
                        # Calculate exponential backoff delay
                        delay = self.retry_delay * (2 ** attempt)
                        
                        self.logger.warning(
                            f"Bedrock API call attempt {attempt + 1}/{self.max_retries} failed with "
                            f"ThrottlingException (request_id={request_id}). Retrying in {delay}s..."
                        )
                        
                        time.sleep(delay)
                        continue
                    else:
                        # All retries exhausted
                        self.logger.error(
                            f"Bedrock API call failed after {self.max_retries} attempts with "
                            f"ThrottlingException (request_id={request_id}): {error_message}"
                        )
                        
                        # Check if fallback to mock is enabled
                        if self.enable_fallback_to_mock:
                            self.logger.warning(
                                "Falling back to mock mode due to repeated throttling errors"
                            )
                            return self._mock_invoke_model(prompt, system_prompt)
                        
                        raise BedrockAPIError(
                            f"Bedrock API throttled after {self.max_retries} retry attempts. "
                            f"Please try again later: {error_message}"
                        ) from e
                
                elif error_code == 'ValidationException':
                    self.logger.error(
                        f"Bedrock API call failed with ValidationException (request_id={request_id}): "
                        f"{error_message}"
                    )
                    raise BedrockAPIError(
                        f"Invalid request parameters: {error_message}"
                    ) from e
                else:
                    self.logger.error(
                        f"Bedrock API call failed with {error_code} (request_id={request_id}): "
                        f"{error_message}"
                    )
                    raise BedrockAPIError(
                        f"Bedrock API error ({error_code}): {error_message}"
                    ) from e
                    
            except Exception as e:
                self.logger.error(
                    f"Unexpected error invoking Bedrock model on attempt {attempt + 1}/{self.max_retries}: "
                    f"{str(e)}"
                )
                raise BedrockAPIError(
                    f"Unexpected error invoking Bedrock model: {str(e)}"
                ) from e
        
        # This should not be reached, but just in case
        if last_error:
            raise BedrockAPIError(
                f"Bedrock API throttled after {self.max_retries} retry attempts"
            ) from last_error
        else:
            raise BedrockAPIError("Unexpected error in retry logic")
    
    def _mock_invoke_model(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mock implementation of invoke_model for testing.
        
        Returns simulated responses based on prompt content.
        """
        self._mock_response_count += 1
        
        # Generate mock response based on prompt keywords
        prompt_lower = prompt.lower()
        
        if 'consumption' in prompt_lower or 'data' in prompt_lower:
            content = (
                "I've analyzed the consumption data. The file contains electricity usage "
                "measurements with timestamps. I've identified the consumption column and "
                "detected a 5-minute interval pattern. The data appears to be from NSW and "
                "covers a period of 7 days with 2,016 intervals."
            )
        elif 'emissions' in prompt_lower or 'calculate' in prompt_lower:
            content = (
                "I've calculated the emissions using both interval-based and annual methods. "
                "The interval-based calculation shows 12.5 tonnes CO2-e, while the annual "
                "method shows 11.8 tonnes CO2-e. This 5.9% difference suggests that your "
                "consumption pattern has slightly higher emissions intensity than the annual average."
            )
        elif 'error' in prompt_lower or 'problem' in prompt_lower:
            content = (
                "I've identified a data quality issue: there are 3 missing time periods in "
                "the sequence, likely due to a data collection gap. This represents 0.15% of "
                "the total data. I recommend proceeding with the calculation, as the impact "
                "on total emissions will be minimal."
            )
        else:
            content = (
                f"Mock response #{self._mock_response_count}: I understand your request. "
                "In production mode, I would use AWS Bedrock with Claude 3 to provide "
                "detailed analysis and insights about your emissions data."
            )
        
        return {
            'content': content,
            'stop_reason': 'end_turn',
            'usage': {
                'input_tokens': len(prompt.split()),
                'output_tokens': len(content.split())
            }
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the Bedrock client configuration.
        
        Returns:
            Dictionary with client configuration details
        """
        return {
            'mode': self.mode.value,
            'model_id': self.model_id,
            'region': self.region,
            'credentials_configured': self._has_credentials(),
            'client_initialized': self._bedrock_runtime is not None or self.mode == BedrockMode.MOCK
        }
    
    def _has_credentials(self) -> bool:
        """
        Check if AWS credentials are configured.
        
        Returns:
            True if credentials are available
        """
        if self.mode == BedrockMode.MOCK:
            return True
        
        # Check explicit credentials
        if self._aws_access_key_id and self._aws_secret_access_key:
            return True
        
        # Check environment variables
        if os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY'):
            return True
        
        # Check if credentials file exists
        credentials_file = os.path.expanduser('~/.aws/credentials')
        if os.path.exists(credentials_file):
            return True
        
        # Assume IAM role might be available (can't check without trying)
        return False


def create_bedrock_client(
    mode: Optional[str] = None,
    **kwargs
) -> BedrockClient:
    """
    Factory function to create a BedrockClient with configuration from environment.
    
    Args:
        mode: Operating mode ('production' or 'mock'). If not provided, reads from
              BEDROCK_MODE environment variable, defaults to 'production'
        **kwargs: Additional arguments passed to BedrockClient constructor
        
    Returns:
        Configured BedrockClient instance
        
    Example:
        >>> # Create client from environment
        >>> client = create_bedrock_client()
        
        >>> # Create mock client
        >>> client = create_bedrock_client(mode='mock')
    """
    # Determine mode
    if mode is None:
        mode = os.environ.get('BEDROCK_MODE', 'production')
    
    bedrock_mode = BedrockMode.PRODUCTION if mode.lower() == 'production' else BedrockMode.MOCK
    
    # Get configuration from environment if not in kwargs
    if 'model_id' not in kwargs:
        kwargs['model_id'] = os.environ.get('BEDROCK_MODEL_ID')
    
    if 'region' not in kwargs:
        kwargs['region'] = os.environ.get('AWS_REGION')
    
    return BedrockClient(mode=bedrock_mode, **kwargs)
