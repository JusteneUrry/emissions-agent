"""
Example usage of EmissionsAgent.

This script demonstrates how to use the EmissionsAgent to autonomously
analyze electricity consumption data and generate emissions insights.
"""

import logging
from agents.emissions_agent import create_emissions_agent
from agents.agent_tools import (
    tool_load_consumption_file,
    tool_identify_consumption_column,
    tool_identify_time_columns,
    tool_parse_emissions_period_code
)


# Configure logging to see agent activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Demonstrate EmissionsAgent usage."""
    
    print("=" * 80)
    print("Emissions Intelligence Agent - Example Usage")
    print("=" * 80)
    print()
    
    # Create agent in mock mode with available tools
    print("1. Creating EmissionsAgent in mock mode...")
    tools = {
        'load_consumption_file': tool_load_consumption_file,
        'identify_consumption_column': tool_identify_consumption_column,
        'identify_time_columns': tool_identify_time_columns,
        'parse_emissions_period_code': tool_parse_emissions_period_code
    }
    
    agent = create_emissions_agent(
        bedrock_mode='mock',
        tools=tools,
        max_retries=3,
        retry_delay=1.0
    )
    
    print(f"   ✓ Agent created with {len(tools)} tools")
    print()
    
    # Get agent info
    print("2. Agent Configuration:")
    info = agent.get_agent_info()
    print(f"   - Bedrock Mode: {info['bedrock_mode']}")
    print(f"   - Model: {info['bedrock_model']}")
    print(f"   - Available Tools: {', '.join(info['available_tools'])}")
    print()
    
    # First interaction - greeting
    print("3. First Interaction:")
    print("   User: Hello! I need help analyzing my electricity consumption data.")
    print()
    
    response = agent.invoke(
        "Hello! I need help analyzing my electricity consumption data.",
        temperature=0.7
    )
    
    print(f"   Agent: {response['content'][:200]}...")
    print(f"   (Stop Reason: {response['stop_reason']}, Tokens: {response['usage']})")
    print()
    
    # Second interaction - specific request
    print("4. Second Interaction:")
    print("   User: I've uploaded a CSV file with consumption data. Can you analyze it?")
    print()
    
    response = agent.invoke(
        "I've uploaded a CSV file with consumption data. Can you analyze it?",
        temperature=0.7
    )
    
    print(f"   Agent: {response['content'][:200]}...")
    if response['tool_calls']:
        print(f"   Tool Calls: {len(response['tool_calls'])} tools invoked")
        for tool_call in response['tool_calls']:
            print(f"      - {tool_call['name']}")
    print()
    
    # View conversation history
    print("5. Conversation History:")
    history = agent.get_conversation_history()
    print(f"   Total messages: {len(history)}")
    for i, msg in enumerate(history, 1):
        role = msg['role'].capitalize()
        content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
        print(f"   {i}. {role}: {content_preview}")
    print()
    
    # View tool invocation log
    print("6. Tool Invocation Log:")
    tool_log = agent.get_tool_invocation_log()
    if tool_log:
        print(f"   Total tool invocations: {len(tool_log)}")
        for i, invocation in enumerate(tool_log, 1):
            tool_name = invocation['tool_name']
            success = invocation['result'].get('success', False)
            status = "✓" if success else "✗"
            print(f"   {i}. {status} {tool_name}")
    else:
        print("   No tools invoked yet")
    print()
    
    # Clear conversation and start fresh
    print("7. Starting New Conversation:")
    agent.clear_conversation()
    print("   ✓ Conversation history cleared")
    
    response = agent.invoke("What can you help me with?")
    print(f"   Agent: {response['content'][:150]}...")
    print()
    
    # Final agent info
    print("8. Final Agent State:")
    final_info = agent.get_agent_info()
    print(f"   - Messages in conversation: {final_info['message_count']}")
    print(f"   - Total tool invocations: {final_info['tool_invocation_count']}")
    print()
    
    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == '__main__':
    main()
