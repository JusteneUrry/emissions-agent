# EmissionsAgent - Autonomous AI Orchestrator

## Overview

The `EmissionsAgent` is an autonomous AI system that orchestrates the emissions calculation workflow using AWS Bedrock's Claude 3 model. It maintains conversation state, selects and invokes appropriate tools, and generates natural language explanations of its reasoning process.

## Key Features

- **Conversation State Management**: Maintains full conversation history across multiple interactions
- **Tool Selection & Invocation**: Autonomously selects and executes appropriate tools based on context
- **Error Handling**: Gracefully handles tool execution failures with user-friendly messages
- **Logging**: Comprehensive logging of all agent activities and tool invocations
- **Mock Mode Support**: Can operate in mock mode for testing without AWS credentials
- **Flexible Tool Registry**: Accepts any callable functions as tools

## Architecture

```
User Prompt → EmissionsAgent → BedrockClient → Claude 3 Model
                    ↓
              Tool Selection
                    ↓
              Tool Execution
                    ↓
           Natural Language Response
```

## Quick Start

### Basic Usage

```python
from agents.emissions_agent import create_emissions_agent
from agents.agent_tools import (
    tool_load_consumption_file,
    tool_identify_consumption_column
)

# Create agent in mock mode
tools = {
    'load_file': tool_load_consumption_file,
    'identify_column': tool_identify_consumption_column
}

agent = create_emissions_agent(
    bedrock_mode='mock',
    tools=tools
)

# Invoke agent
response = agent.invoke("Analyze my consumption data")
print(response['content'])
```

### Production Mode

```python
# Create agent in production mode (requires AWS credentials)
agent = create_emissions_agent(
    bedrock_mode='production',
    tools=tools,
    max_retries=3,
    retry_delay=1.0
)

response = agent.invoke("Load the uploaded consumption file")
```

## Core Components

### EmissionsAgent Class

The main agent orchestrator that wraps BedrockClient and manages the workflow.

**Key Methods:**

- `invoke(prompt, max_tokens, temperature, include_history)`: Main entry point for agent interaction
- `add_message(role, content, tool_calls, tool_results)`: Add messages to conversation history
- `get_conversation_history()`: Retrieve full conversation history
- `clear_conversation()`: Clear conversation state for new session
- `get_tool_invocation_log()`: Get log of all tool executions
- `get_agent_info()`: Get agent configuration information

### ConversationState Class

Manages conversation history and tool invocation tracking.

**Attributes:**

- `messages`: List of Message objects representing the conversation
- `tool_invocations`: List of tool execution records

### Message Dataclass

Represents a single message in the conversation.

**Fields:**

- `role`: Message role ("user", "assistant", or "tool")
- `content`: Message content
- `tool_calls`: Optional list of tool calls made by the assistant
- `tool_results`: Optional list of tool execution results

## Tool Integration

### Tool Function Format

Tools should be callable functions that return a dictionary with the following structure:

```python
def my_tool(arg1: str, arg2: int) -> Dict[str, Any]:
    """Tool description."""
    try:
        # Tool logic here
        result = do_something(arg1, arg2)
        
        return {
            'success': True,
            'result': result,
            'message': 'Tool executed successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': f'Tool failed: {str(e)}'
        }
```

### Registering Tools

```python
tools = {
    'tool_name': tool_function,
    'another_tool': another_function
}

agent = EmissionsAgent(bedrock_client, tools)
```

### Tool Call Parsing

The agent parses tool calls from the model's response using the format:

```
TOOL_CALL: tool_name(arg1=value1, arg2=value2)
```

**Note**: This is a simplified implementation. Production systems would use Bedrock's native tool calling format.

## Conversation Management

### Adding Messages

```python
# Add user message
agent.add_message("user", "Analyze my data")

# Add assistant message with tool calls
agent.add_message(
    "assistant",
    "I'll load the file",
    tool_calls=[{'name': 'load_file', 'arguments': {'path': 'data.csv'}}]
)
```

### Viewing History

```python
history = agent.get_conversation_history()
for msg in history:
    print(f"{msg['role']}: {msg['content']}")
```

### Clearing History

```python
# Start fresh conversation
agent.clear_conversation()
```

## Error Handling

The agent handles errors at multiple levels:

### Tool Execution Errors

```python
# Tool not found
result = agent._execute_single_tool('nonexistent_tool', {})
# Returns: {'success': False, 'error': 'Tool not found', ...}

# Tool raises exception
result = agent._execute_single_tool('failing_tool', {})
# Returns: {'success': False, 'error': 'Exception message', ...}
```

### Bedrock API Errors

The underlying BedrockClient handles:
- Throttling with exponential backoff retry
- Authentication errors
- Connection failures
- Graceful degradation to mock mode (if enabled)

## Logging

The agent uses Python's logging module with the logger name `'emissions_agent'`.

### Configure Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Log Levels

- **INFO**: Agent initialization, invocations, tool executions
- **DEBUG**: Message additions, tool call parsing details
- **ERROR**: Tool execution failures, API errors

## System Prompt

The agent uses a default system prompt that defines its behavior and capabilities. You can customize it:

```python
custom_prompt = """You are a specialized emissions agent that...
Your capabilities include...
Your approach is..."""

agent = EmissionsAgent(
    bedrock_client,
    tools,
    system_prompt=custom_prompt
)
```

## Factory Function

The `create_emissions_agent()` factory function provides a convenient way to create agents:

```python
agent = create_emissions_agent(
    bedrock_mode='mock',           # or 'production'
    tools=my_tools,                # optional
    max_retries=3,                 # BedrockClient parameter
    retry_delay=1.0,               # BedrockClient parameter
    enable_fallback_to_mock=False  # BedrockClient parameter
)
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest test_emissions_agent.py -v
```

The test suite covers:
- ConversationState management
- Agent initialization
- Message handling
- Tool execution (success and failure cases)
- Tool call parsing
- Agent invocation
- Error recovery
- Integration workflows

### Example Script

Run the example demonstration:

```bash
cd emissions-dashboard
python agents/emissions_agent_example.py
```

## Integration with Existing Modules

The agent integrates with existing emissions modules through tool wrappers:

```python
from agents.agent_tools import (
    tool_load_consumption_file,
    tool_identify_consumption_column,
    tool_identify_time_columns,
    tool_parse_emissions_period_code
)

tools = {
    'load_file': tool_load_consumption_file,
    'identify_consumption': tool_identify_consumption_column,
    'identify_time': tool_identify_time_columns,
    'parse_code': tool_parse_emissions_period_code
}

agent = create_emissions_agent(bedrock_mode='mock', tools=tools)
```

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 0.2**: Natural Language Insight Generation
  - Agent generates natural language responses via Claude 3
  - Maintains conversation context for coherent dialogue
  
- **Requirement 0.4**: Agent Observability and Control
  - Full conversation history tracking
  - Tool invocation logging
  - Agent configuration information available

## Future Enhancements

1. **Native Bedrock Tool Calling**: Migrate from regex-based parsing to Bedrock's native tool calling format
2. **Streaming Responses**: Support streaming for real-time agent responses
3. **Multi-Turn Tool Execution**: Allow agent to make multiple tool calls in sequence
4. **Tool Result Feedback**: Feed tool results back to the model for follow-up reasoning
5. **Conversation Persistence**: Save and restore conversation state across sessions

## API Reference

### EmissionsAgent

```python
class EmissionsAgent:
    def __init__(
        self,
        bedrock_client: BedrockClient,
        tools: Dict[str, Callable],
        system_prompt: Optional[str] = None
    )
    
    def invoke(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        include_history: bool = True
    ) -> Dict[str, Any]
    
    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> None
    
    def get_conversation_history(self) -> List[Dict[str, Any]]
    
    def clear_conversation(self) -> None
    
    def get_tool_invocation_log(self) -> List[Dict[str, Any]]
    
    def get_agent_info(self) -> Dict[str, Any]
```

### Factory Function

```python
def create_emissions_agent(
    bedrock_mode: str = "production",
    tools: Optional[Dict[str, Callable]] = None,
    **bedrock_kwargs
) -> EmissionsAgent
```

## See Also

- `bedrock_client.py` - AWS Bedrock integration
- `agent_tools.py` - Tool wrappers for emissions modules
- `BEDROCK_CLIENT_README.md` - BedrockClient documentation
- `README.md` - Agent tools overview
- `AGENT_ARCHITECTURE.md` - High-level architecture documentation
