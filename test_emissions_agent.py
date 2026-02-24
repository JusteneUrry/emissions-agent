"""
Tests for EmissionsAgent class.

This module tests the EmissionsAgent's ability to:
- Maintain conversation state
- Invoke tools based on parsed requests
- Handle errors gracefully
- Integrate with BedrockClient
"""

import pytest
from agents.emissions_agent import (
    EmissionsAgent,
    ConversationState,
    Message,
    create_emissions_agent
)
from agents.bedrock_client import BedrockClient, BedrockMode


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_bedrock_client():
    """Create a BedrockClient in mock mode."""
    return BedrockClient(mode=BedrockMode.MOCK)


@pytest.fixture
def sample_tools():
    """Create sample tool functions for testing."""
    def mock_load_file(file_path: str):
        return {
            'success': True,
            'result': {'rows': 100, 'columns': ['timestamp', 'consumption']},
            'message': f'Loaded file: {file_path}'
        }
    
    def mock_identify_column(dataframe: dict):
        return {
            'success': True,
            'result': 'consumption_kwh',
            'message': 'Identified consumption column'
        }
    
    def mock_failing_tool():
        raise ValueError("Tool execution failed")
    
    return {
        'load_file': mock_load_file,
        'identify_column': mock_identify_column,
        'failing_tool': mock_failing_tool
    }


@pytest.fixture
def emissions_agent(mock_bedrock_client, sample_tools):
    """Create an EmissionsAgent with mock client and tools."""
    return EmissionsAgent(mock_bedrock_client, sample_tools)


# ============================================================================
# ConversationState Tests
# ============================================================================

def test_conversation_state_initialization():
    """Test ConversationState initializes with empty lists."""
    state = ConversationState()
    assert len(state.messages) == 0
    assert len(state.tool_invocations) == 0


def test_conversation_state_add_message():
    """Test adding messages to conversation state."""
    state = ConversationState()
    
    state.add_message("user", "Hello")
    assert len(state.messages) == 1
    assert state.messages[0].role == "user"
    assert state.messages[0].content == "Hello"
    
    state.add_message("assistant", "Hi there")
    assert len(state.messages) == 2
    assert state.messages[1].role == "assistant"


def test_conversation_state_with_tool_calls():
    """Test adding messages with tool calls."""
    state = ConversationState()
    
    tool_calls = [{'name': 'load_file', 'arguments': {'file_path': 'data.csv'}}]
    state.add_message("assistant", "Loading file", tool_calls=tool_calls)
    
    assert state.messages[0].tool_calls == tool_calls


def test_conversation_state_get_history():
    """Test getting conversation history."""
    state = ConversationState()
    
    state.add_message("user", "Hello")
    state.add_message("assistant", "Hi")
    
    history = state.get_history()
    assert len(history) == 2
    assert history[0]['role'] == "user"
    assert history[0]['content'] == "Hello"
    assert history[1]['role'] == "assistant"


def test_conversation_state_clear():
    """Test clearing conversation state."""
    state = ConversationState()
    
    state.add_message("user", "Hello")
    state.add_message("assistant", "Hi")
    assert len(state.messages) == 2
    
    state.clear()
    assert len(state.messages) == 0
    assert len(state.tool_invocations) == 0


# ============================================================================
# EmissionsAgent Initialization Tests
# ============================================================================

def test_emissions_agent_initialization(mock_bedrock_client, sample_tools):
    """Test EmissionsAgent initializes correctly."""
    agent = EmissionsAgent(mock_bedrock_client, sample_tools)
    
    assert agent.bedrock_client == mock_bedrock_client
    assert agent.tools == sample_tools
    assert len(agent.conversation.messages) == 0
    assert agent.system_prompt == EmissionsAgent.DEFAULT_SYSTEM_PROMPT


def test_emissions_agent_custom_system_prompt(mock_bedrock_client, sample_tools):
    """Test EmissionsAgent with custom system prompt."""
    custom_prompt = "You are a custom emissions agent."
    agent = EmissionsAgent(mock_bedrock_client, sample_tools, system_prompt=custom_prompt)
    
    assert agent.system_prompt == custom_prompt


def test_emissions_agent_empty_tools(mock_bedrock_client):
    """Test EmissionsAgent can be initialized with no tools."""
    agent = EmissionsAgent(mock_bedrock_client, {})
    
    assert len(agent.tools) == 0
    assert agent.bedrock_client == mock_bedrock_client


# ============================================================================
# Conversation Management Tests
# ============================================================================

def test_add_message(emissions_agent):
    """Test adding messages to agent conversation."""
    emissions_agent.add_message("user", "Analyze my data")
    
    assert len(emissions_agent.conversation.messages) == 1
    assert emissions_agent.conversation.messages[0].role == "user"
    assert emissions_agent.conversation.messages[0].content == "Analyze my data"


def test_get_conversation_history(emissions_agent):
    """Test getting conversation history."""
    emissions_agent.add_message("user", "Hello")
    emissions_agent.add_message("assistant", "Hi there")
    
    history = emissions_agent.get_conversation_history()
    
    assert len(history) == 2
    assert history[0]['role'] == "user"
    assert history[1]['role'] == "assistant"


def test_clear_conversation(emissions_agent):
    """Test clearing conversation history."""
    emissions_agent.add_message("user", "Hello")
    emissions_agent.add_message("assistant", "Hi")
    
    assert len(emissions_agent.conversation.messages) == 2
    
    emissions_agent.clear_conversation()
    
    assert len(emissions_agent.conversation.messages) == 0


# ============================================================================
# Tool Execution Tests
# ============================================================================

def test_execute_single_tool_success(emissions_agent):
    """Test successful tool execution."""
    result = emissions_agent._execute_single_tool(
        'load_file',
        {'file_path': 'test.csv'}
    )
    
    assert result['success'] is True
    assert 'Loaded file: test.csv' in result['message']
    assert result['result']['rows'] == 100


def test_execute_single_tool_not_found(emissions_agent):
    """Test executing a non-existent tool."""
    result = emissions_agent._execute_single_tool(
        'nonexistent_tool',
        {}
    )
    
    assert result['success'] is False
    assert 'not found' in result['error']
    assert result['error_type'] == 'ToolNotFoundError'


def test_execute_single_tool_exception(emissions_agent):
    """Test tool execution that raises an exception."""
    result = emissions_agent._execute_single_tool(
        'failing_tool',
        {}
    )
    
    assert result['success'] is False
    assert 'Tool execution failed' in result['error']
    assert result['error_type'] == 'ValueError'


def test_execute_tools_multiple(emissions_agent):
    """Test executing multiple tools."""
    tool_calls = [
        {'name': 'load_file', 'arguments': {'file_path': 'data.csv'}},
        {'name': 'identify_column', 'arguments': {'dataframe': {}}}
    ]
    
    results = emissions_agent._execute_tools(tool_calls)
    
    assert len(results) == 2
    assert results[0]['success'] is True
    assert results[1]['success'] is True
    assert len(emissions_agent.conversation.tool_invocations) == 2


# ============================================================================
# Tool Call Parsing Tests
# ============================================================================

def test_parse_tool_calls_single():
    """Test parsing a single tool call from content."""
    agent = EmissionsAgent(BedrockClient(mode=BedrockMode.MOCK), {})
    
    content = "I'll load the file. TOOL_CALL: load_file(file_path='data.csv')"
    tool_calls = agent._parse_tool_calls(content)
    
    assert len(tool_calls) == 1
    assert tool_calls[0]['name'] == 'load_file'
    assert tool_calls[0]['arguments']['file_path'] == 'data.csv'


def test_parse_tool_calls_multiple():
    """Test parsing multiple tool calls from content."""
    agent = EmissionsAgent(BedrockClient(mode=BedrockMode.MOCK), {})
    
    content = """
    I'll analyze your data.
    TOOL_CALL: load_file(file_path='data.csv')
    TOOL_CALL: identify_column(dataframe='df')
    """
    tool_calls = agent._parse_tool_calls(content)
    
    assert len(tool_calls) == 2
    assert tool_calls[0]['name'] == 'load_file'
    assert tool_calls[1]['name'] == 'identify_column'


def test_parse_tool_calls_none():
    """Test parsing content with no tool calls."""
    agent = EmissionsAgent(BedrockClient(mode=BedrockMode.MOCK), {})
    
    content = "I understand your request. Let me help you with that."
    tool_calls = agent._parse_tool_calls(content)
    
    assert len(tool_calls) == 0


# ============================================================================
# Agent Invocation Tests
# ============================================================================

def test_invoke_basic(emissions_agent):
    """Test basic agent invocation."""
    response = emissions_agent.invoke("Analyze my consumption data")
    
    assert 'content' in response
    assert 'stop_reason' in response
    assert 'usage' in response
    assert isinstance(response['content'], str)
    assert len(response['content']) > 0


def test_invoke_adds_to_history(emissions_agent):
    """Test that invoke adds messages to conversation history."""
    initial_count = len(emissions_agent.conversation.messages)
    
    emissions_agent.invoke("Hello")
    
    # Should add user message and assistant response
    assert len(emissions_agent.conversation.messages) > initial_count


def test_invoke_without_history(emissions_agent):
    """Test invoking agent without including conversation history."""
    emissions_agent.add_message("user", "Previous message")
    
    response = emissions_agent.invoke("New message", include_history=False)
    
    assert 'content' in response
    # Should still add messages to history even if not including it in prompt
    assert len(emissions_agent.conversation.messages) >= 2


def test_invoke_with_custom_parameters(emissions_agent):
    """Test invoking agent with custom parameters."""
    response = emissions_agent.invoke(
        "Analyze data",
        max_tokens=2048,
        temperature=0.5
    )
    
    assert 'content' in response
    assert 'usage' in response


# ============================================================================
# Tool Invocation Log Tests
# ============================================================================

def test_get_tool_invocation_log_empty(emissions_agent):
    """Test getting tool invocation log when no tools have been called."""
    log = emissions_agent.get_tool_invocation_log()
    
    assert len(log) == 0


def test_get_tool_invocation_log_with_invocations(emissions_agent):
    """Test getting tool invocation log after executing tools."""
    tool_calls = [
        {'name': 'load_file', 'arguments': {'file_path': 'data.csv'}}
    ]
    
    emissions_agent._execute_tools(tool_calls)
    
    log = emissions_agent.get_tool_invocation_log()
    
    assert len(log) == 1
    assert log[0]['tool_name'] == 'load_file'
    assert log[0]['arguments']['file_path'] == 'data.csv'
    assert 'result' in log[0]


# ============================================================================
# Agent Info Tests
# ============================================================================

def test_get_agent_info(emissions_agent):
    """Test getting agent configuration information."""
    info = emissions_agent.get_agent_info()
    
    assert 'bedrock_mode' in info
    assert 'bedrock_model' in info
    assert 'tool_count' in info
    assert 'available_tools' in info
    assert 'message_count' in info
    assert 'tool_invocation_count' in info
    
    assert info['bedrock_mode'] == 'mock'
    assert info['tool_count'] == 3  # From sample_tools fixture
    assert 'load_file' in info['available_tools']


def test_get_agent_info_after_conversation(emissions_agent):
    """Test agent info reflects conversation state."""
    emissions_agent.add_message("user", "Hello")
    emissions_agent.add_message("assistant", "Hi")
    
    info = emissions_agent.get_agent_info()
    
    assert info['message_count'] == 2


# ============================================================================
# Factory Function Tests
# ============================================================================

def test_create_emissions_agent_mock_mode():
    """Test creating agent in mock mode."""
    agent = create_emissions_agent(bedrock_mode='mock')
    
    assert agent.bedrock_client.mode == BedrockMode.MOCK
    assert len(agent.tools) == 0  # No default tools


def test_create_emissions_agent_production_mode():
    """Test creating agent in production mode."""
    try:
        agent = create_emissions_agent(bedrock_mode='production')
        assert agent.bedrock_client.mode == BedrockMode.PRODUCTION
    except Exception as e:
        # Production mode requires boto3, which may not be installed in test environment
        # This is expected behavior
        assert 'boto3' in str(e).lower() or 'credentials' in str(e).lower()
        pytest.skip("boto3 not available for production mode testing")


def test_create_emissions_agent_with_tools():
    """Test creating agent with custom tools."""
    def custom_tool():
        return {'success': True}
    
    tools = {'custom': custom_tool}
    agent = create_emissions_agent(bedrock_mode='mock', tools=tools)
    
    assert 'custom' in agent.tools
    assert agent.tools['custom'] == custom_tool


def test_create_emissions_agent_with_bedrock_kwargs():
    """Test creating agent with custom Bedrock parameters."""
    agent = create_emissions_agent(
        bedrock_mode='mock',
        max_retries=5,
        retry_delay=2.0
    )
    
    assert agent.bedrock_client.max_retries == 5
    assert agent.bedrock_client.retry_delay == 2.0


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_mock_mode():
    """Test a complete workflow in mock mode."""
    # Create agent
    def mock_tool(data: str):
        return {
            'success': True,
            'result': f'Processed: {data}',
            'message': 'Tool executed successfully'
        }
    
    tools = {'process_data': mock_tool}
    agent = create_emissions_agent(bedrock_mode='mock', tools=tools)
    
    # Invoke agent
    response = agent.invoke("Process my consumption data")
    
    # Verify response
    assert response['content']
    assert response['stop_reason'] == 'end_turn'
    
    # Verify conversation history
    history = agent.get_conversation_history()
    assert len(history) >= 2  # User message + assistant response
    
    # Get agent info
    info = agent.get_agent_info()
    assert info['message_count'] >= 2


def test_error_recovery():
    """Test agent handles tool execution errors gracefully."""
    def failing_tool():
        raise RuntimeError("Simulated failure")
    
    tools = {'fail': failing_tool}
    agent = create_emissions_agent(bedrock_mode='mock', tools=tools)
    
    # Execute failing tool directly
    result = agent._execute_single_tool('fail', {})
    
    # Should return error result, not raise exception
    assert result['success'] is False
    assert 'Simulated failure' in result['error']


def test_conversation_continuity():
    """Test that conversation state is maintained across multiple invocations."""
    agent = create_emissions_agent(bedrock_mode='mock')
    
    # First invocation
    agent.invoke("Hello")
    first_count = len(agent.conversation.messages)
    
    # Second invocation
    agent.invoke("How are you?")
    second_count = len(agent.conversation.messages)
    
    # Should have more messages after second invocation
    assert second_count > first_count
    
    # History should include both conversations
    history = agent.get_conversation_history()
    assert len(history) == second_count


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
