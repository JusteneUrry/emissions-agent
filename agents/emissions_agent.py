"""
Emissions Intelligence Agent - Autonomous AI orchestrator for emissions analysis.

This module implements the EmissionsAgent class that wraps AWS Bedrock's Claude 3 model
to autonomously analyze electricity consumption data and generate emissions insights.

The agent maintains conversation state, selects and invokes appropriate tools from the
emissions modules, and generates natural language explanations of its reasoning process.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from agents.bedrock_client import BedrockClient, BedrockMode


# Set up logger
logger = logging.getLogger('emissions_agent')


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # "user", "assistant", or "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


@dataclass
class ConversationState:
    """Manages conversation history and context."""
    messages: List[Message] = field(default_factory=list)
    tool_invocations: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str, 
                   tool_calls: Optional[List[Dict[str, Any]]] = None,
                   tool_results: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add a message to the conversation history."""
        message = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results
        )
        self.messages.append(message)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history in a format suitable for Bedrock."""
        history = []
        for msg in self.messages:
            msg_dict = {
                'role': msg.role,
                'content': msg.content
            }
            if msg.tool_calls:
                msg_dict['tool_calls'] = msg.tool_calls
            if msg.tool_results:
                msg_dict['tool_results'] = msg.tool_results
            history.append(msg_dict)
        return history
    
    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
        self.tool_invocations.clear()


class EmissionsAgent:
    """
    Autonomous AI agent for emissions analysis using AWS Bedrock.
    
    The EmissionsAgent orchestrates the emissions calculation workflow by:
    1. Maintaining conversation state across multiple interactions
    2. Selecting and invoking appropriate tools based on context
    3. Generating natural language explanations of findings
    4. Handling errors gracefully with user-friendly messages
    
    The agent wraps a BedrockClient and exposes emissions modules as callable tools.
    
    Attributes:
        bedrock_client: BedrockClient instance for AWS Bedrock API calls
        tools: Dictionary mapping tool names to callable functions
        conversation: ConversationState managing conversation history
        system_prompt: System prompt defining agent behavior and capabilities
        
    Example:
        >>> from agents.bedrock_client import BedrockClient, BedrockMode
        >>> from agents.agent_tools import tool_load_consumption_file
        >>> 
        >>> # Initialize client and agent
        >>> client = BedrockClient(mode=BedrockMode.MOCK)
        >>> tools = {'load_consumption_file': tool_load_consumption_file}
        >>> agent = EmissionsAgent(client, tools)
        >>> 
        >>> # Invoke agent with a prompt
        >>> response = agent.invoke("Analyze the uploaded consumption data")
        >>> print(response['content'])
    """
    
    # Default system prompt for the emissions agent
    DEFAULT_SYSTEM_PROMPT = """You are an Emissions Intelligence Agent specialized in analyzing electricity consumption data and calculating greenhouse gas emissions.

Your capabilities:
- Load and parse electricity consumption data from CSV and Excel files
- Identify consumption, timestamp, and time period columns automatically
- Detect data intervals (5-minute or 30-minute) from patterns
- Validate data quality and identify issues (missing periods, duplicates, negative values)
- Load emissions factors for Australian NEM states (NSW, VIC, QLD, SA, TAS)
- Calculate emissions using both interval-based and annual comparison methods
- Generate visualizations and insights about emissions patterns
- Provide actionable recommendations for emissions reduction

Your approach:
- Be autonomous: Make reasonable inferences and proceed with minimal user input
- Be transparent: Explain your reasoning and assumptions clearly
- Be helpful: Provide context and insights, not just calculations
- Be accurate: Use the correct tools and validate your work
- Be conversational: Communicate in natural, friendly language

When analyzing data:
1. Start by understanding the data structure (columns, format, interval)
2. Validate data quality and warn about issues
3. Gather necessary context (e.g., NEM state selection)
4. Perform calculations using appropriate methods
5. Generate insights by comparing results and identifying patterns
6. Provide recommendations based on findings

Always explain what you're doing and why. If you encounter errors or ambiguities, explain them clearly and suggest solutions."""
    
    def __init__(
        self,
        bedrock_client: BedrockClient,
        tools: Dict[str, Callable],
        system_prompt: Optional[str] = None
    ):
        """
        Initialize the EmissionsAgent.
        
        Args:
            bedrock_client: BedrockClient instance for AWS Bedrock API calls
            tools: Dictionary mapping tool names to callable functions
                   Each tool should accept appropriate parameters and return a dict
                   with 'success', 'result', and 'message' keys
            system_prompt: Optional custom system prompt (uses DEFAULT_SYSTEM_PROMPT if not provided)
            
        Example:
            >>> client = BedrockClient(mode=BedrockMode.PRODUCTION)
            >>> tools = {
            ...     'load_file': tool_load_consumption_file,
            ...     'identify_columns': tool_identify_consumption_column
            ... }
            >>> agent = EmissionsAgent(client, tools)
        """
        self.bedrock_client = bedrock_client
        self.tools = tools
        self.conversation = ConversationState()
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        logger.info(
            f"Initialized EmissionsAgent with {len(tools)} tools: {list(tools.keys())}"
        )
    
    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role ("user", "assistant", or "tool")
            content: Message content
            tool_calls: Optional list of tool calls made by the assistant
            tool_results: Optional list of tool execution results
            
        Example:
            >>> agent.add_message("user", "Analyze my consumption data")
            >>> agent.add_message("assistant", "I'll load and analyze your data", 
            ...                   tool_calls=[{'name': 'load_file', 'args': {...}}])
        """
        self.conversation.add_message(role, content, tool_calls, tool_results)
        logger.debug(f"Added {role} message to conversation: {content[:100]}...")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the full conversation history.
        
        Returns:
            List of message dictionaries with role, content, and optional tool information
            
        Example:
            >>> history = agent.get_conversation_history()
            >>> for msg in history:
            ...     print(f"{msg['role']}: {msg['content']}")
        """
        return self.conversation.get_history()
    
    def clear_conversation(self) -> None:
        """
        Clear the conversation history.
        
        Useful for starting a new analysis session without creating a new agent instance.
        
        Example:
            >>> agent.clear_conversation()
            >>> # Start fresh conversation
            >>> agent.invoke("Analyze new data")
        """
        self.conversation.clear()
        logger.info("Cleared conversation history")
    
    def invoke(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """
        Invoke the agent with a user prompt.
        
        This is the main entry point for interacting with the agent. The agent will:
        1. Add the user prompt to conversation history
        2. Call the Bedrock model with the prompt and system context
        3. Parse the response for tool calls
        4. Execute any requested tools
        5. Return the agent's response with tool results
        
        Args:
            prompt: User prompt or question
            max_tokens: Maximum tokens in response (default: 4096)
            temperature: Sampling temperature 0.0-1.0 (default: 0.7)
            include_history: Whether to include conversation history in the request (default: True)
            
        Returns:
            Dictionary with keys:
            - 'content': Agent's natural language response
            - 'tool_calls': List of tools the agent attempted to call (if any)
            - 'tool_results': Results from tool executions (if any)
            - 'stop_reason': Reason for completion
            - 'usage': Token usage statistics
            
        Raises:
            Exception: If Bedrock API call fails or tool execution fails critically
            
        Example:
            >>> response = agent.invoke("Load the consumption data from uploaded file")
            >>> print(response['content'])
            >>> if response['tool_calls']:
            ...     print(f"Agent called {len(response['tool_calls'])} tools")
        """
        # Add user message to history
        self.add_message("user", prompt)
        
        # Build the full prompt with history if requested
        if include_history and len(self.conversation.messages) > 1:
            # Format conversation history
            history_text = self._format_conversation_history()
            full_prompt = f"{history_text}\n\nUser: {prompt}"
        else:
            full_prompt = prompt
        
        logger.info(f"Invoking agent with prompt: {prompt[:100]}...")
        
        try:
            # Call Bedrock model
            response = self.bedrock_client.invoke_model(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=self.system_prompt
            )
            
            content = response['content']
            stop_reason = response['stop_reason']
            usage = response['usage']
            
            logger.info(
                f"Bedrock response received: {len(content)} chars, "
                f"stop_reason={stop_reason}, tokens={usage}"
            )
            
            # Parse response for tool calls
            tool_calls = self._parse_tool_calls(content)
            tool_results = []
            
            # Execute any tool calls
            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool calls")
                tool_results = self._execute_tools(tool_calls)
                
                # Add assistant message with tool calls to history
                self.add_message(
                    "assistant",
                    content,
                    tool_calls=tool_calls,
                    tool_results=tool_results
                )
            else:
                # Add assistant message without tool calls
                self.add_message("assistant", content)
            
            return {
                'content': content,
                'tool_calls': tool_calls,
                'tool_results': tool_results,
                'stop_reason': stop_reason,
                'usage': usage
            }
            
        except Exception as e:
            logger.error(f"Error invoking agent: {str(e)}", exc_info=True)
            error_message = f"I encountered an error: {str(e)}"
            self.add_message("assistant", error_message)
            raise
    
    def _format_conversation_history(self) -> str:
        """
        Format conversation history as a text string for inclusion in prompts.
        
        Returns:
            Formatted conversation history string
        """
        history_parts = []
        for msg in self.conversation.messages[:-1]:  # Exclude the current message
            if msg.role == "user":
                history_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                history_parts.append(f"Assistant: {msg.content}")
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        history_parts.append(
                            f"  [Tool: {tool_call['name']} with args {tool_call['arguments']}]"
                        )
                if msg.tool_results:
                    for tool_result in msg.tool_results:
                        success = tool_result.get('success', False)
                        status = "✓" if success else "✗"
                        history_parts.append(
                            f"  [Result {status}: {tool_result.get('message', 'No message')}]"
                        )
        
        return "\n".join(history_parts)
    
    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse the agent's response for tool call requests.
        
        This method looks for tool call patterns in the agent's response.
        The expected format is JSON-like tool call specifications.
        
        For now, this is a simple implementation that looks for specific patterns.
        In a production system, this would use Bedrock's native tool calling format.
        
        Args:
            content: Agent's response content
            
        Returns:
            List of tool call dictionaries with 'name' and 'arguments' keys
        """
        tool_calls = []
        
        # Simple pattern matching for tool calls
        # Format: TOOL_CALL: tool_name(arg1=value1, arg2=value2)
        # This is a simplified version - production would use structured tool calling
        
        import re
        pattern = r'TOOL_CALL:\s*(\w+)\((.*?)\)'
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        for match in matches:
            tool_name = match.group(1)
            args_str = match.group(2)
            
            # Parse arguments (simplified - assumes key=value format)
            arguments = {}
            if args_str.strip():
                for arg in args_str.split(','):
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        arguments[key.strip()] = value.strip().strip('"\'')
            
            tool_calls.append({
                'name': tool_name,
                'arguments': arguments
            })
            
            logger.debug(f"Parsed tool call: {tool_name} with args {arguments}")
        
        return tool_calls
    
    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute a list of tool calls.
        
        Args:
            tool_calls: List of tool call dictionaries with 'name' and 'arguments'
            
        Returns:
            List of tool execution results
        """
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call['name']
            arguments = tool_call['arguments']
            
            result = self._execute_single_tool(tool_name, arguments)
            results.append(result)
            
            # Log tool invocation
            self.conversation.tool_invocations.append({
                'tool_name': tool_name,
                'arguments': arguments,
                'result': result
            })
        
        return results
    
    def _execute_single_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments to pass to the tool
            
        Returns:
            Tool execution result dictionary with 'success', 'result', and 'message' keys
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        # Check if tool exists
        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not found. Available tools: {list(self.tools.keys())}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'ToolNotFoundError',
                'message': f"Unknown tool: {tool_name}"
            }
        
        # Get tool function
        tool_func = self.tools[tool_name]
        
        try:
            # Execute tool
            result = tool_func(**arguments)
            
            # Ensure result has expected structure
            if not isinstance(result, dict):
                result = {
                    'success': True,
                    'result': result,
                    'message': f"Tool {tool_name} executed successfully"
                }
            
            logger.info(
                f"Tool {tool_name} executed: success={result.get('success', True)}"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'message': error_msg
            }
    
    def get_tool_invocation_log(self) -> List[Dict[str, Any]]:
        """
        Get the log of all tool invocations in the current conversation.
        
        Returns:
            List of tool invocation records with tool name, arguments, and results
            
        Example:
            >>> log = agent.get_tool_invocation_log()
            >>> for invocation in log:
            ...     print(f"Tool: {invocation['tool_name']}")
            ...     print(f"Success: {invocation['result']['success']}")
        """
        return self.conversation.tool_invocations.copy()
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the agent configuration.
        
        Returns:
            Dictionary with agent configuration details
            
        Example:
            >>> info = agent.get_agent_info()
            >>> print(f"Agent has {info['tool_count']} tools available")
            >>> print(f"Conversation has {info['message_count']} messages")
        """
        return {
            'bedrock_mode': self.bedrock_client.mode.value,
            'bedrock_model': self.bedrock_client.model_id,
            'tool_count': len(self.tools),
            'available_tools': list(self.tools.keys()),
            'message_count': len(self.conversation.messages),
            'tool_invocation_count': len(self.conversation.tool_invocations),
            'system_prompt_length': len(self.system_prompt)
        }
    
    def analyze_consumption_data(
        self,
        uploaded_file: Any,
        state: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Orchestrate the full autonomous analysis workflow for consumption data.
        
        This method chains multiple tool calls to:
        1. Load the uploaded file
        2. Identify consumption and time columns
        3. Detect the data interval
        4. Validate data quality
        5. Load emissions factors
        6. Calculate emissions using both interval and annual methods
        
        The agent generates natural language explanations at each step per
        Requirements 0.2.1, 0.2.2, 0.2.3, 0.5, and 0.6.
        
        Args:
            uploaded_file: Streamlit UploadedFile object with consumption data
            state: NEM state code (NSW, VIC, QLD, SA, TAS)
            max_tokens: Maximum tokens for each agent invocation (default: 4096)
            temperature: Sampling temperature 0.0-1.0 (default: 0.7)
            
        Returns:
            Dictionary with keys:
            - 'success': Boolean indicating if analysis completed successfully
            - 'results': Dictionary containing calculation results if successful
            - 'insights': Natural language insights about the emissions
            - 'reasoning_trace': List of decision points and explanations
            - 'error': Error message if analysis failed
            
        Example:
            >>> agent = create_emissions_agent(bedrock_mode='mock')
            >>> result = agent.analyze_consumption_data(uploaded_file, 'NSW')
            >>> if result['success']:
            ...     print(result['insights'])
            ...     print(f"Total emissions: {result['results']['interval_total']}")
        """
        logger.info(
            f"Starting autonomous analysis workflow for file: {uploaded_file.name}, state: {state}"
        )
        
        reasoning_trace = []
        
        try:
            # Step 1: Load file
            prompt = f"""I need you to analyze electricity consumption data from the uploaded file '{uploaded_file.name}'.

First, load the file and tell me what you find - how many rows, what columns are present, and what the data looks like."""
            
            response = self.invoke(prompt, max_tokens=max_tokens, temperature=temperature)
            reasoning_trace.append({
                'step': 'file_loading',
                'decision': 'Load and understand data structure',
                'explanation': response['content'],
                'tool_calls': response.get('tool_calls', [])
            })
            
            # Step 2: Identify columns and detect interval
            prompt = f"""Now identify the consumption column and time-related columns (timestamp, date, period).

Then detect whether this is 5-minute or 30-minute interval data. Explain your reasoning clearly."""
            
            response = self.invoke(prompt, max_tokens=max_tokens, temperature=temperature)
            reasoning_trace.append({
                'step': 'structure_detection',
                'decision': 'Identify columns and detect interval',
                'explanation': response['content'],
                'tool_calls': response.get('tool_calls', [])
            })
            
            # Step 3: Validate data quality
            prompt = """Validate the data quality by checking for:
- Missing time periods in the sequence
- Duplicate time periods (potential DST transitions)
- Negative consumption values

Explain any issues you find in user-friendly terms."""
            
            response = self.invoke(prompt, max_tokens=max_tokens, temperature=temperature)
            reasoning_trace.append({
                'step': 'data_validation',
                'decision': 'Validate data quality',
                'explanation': response['content'],
                'tool_calls': response.get('tool_calls', [])
            })
            
            # Step 4: Load emissions factors
            prompt = f"""Load the emissions factors for {state} state. You'll need both:
1. Interval-specific factors (matching the detected interval)
2. Annual average factors for comparison

Explain what factors you're loading and why."""
            
            response = self.invoke(prompt, max_tokens=max_tokens, temperature=temperature)
            reasoning_trace.append({
                'step': 'factor_loading',
                'decision': f'Load emissions factors for {state}',
                'explanation': response['content'],
                'tool_calls': response.get('tool_calls', [])
            })
            
            # Step 5: Calculate emissions
            prompt = """Now calculate the emissions using both methods:
1. Interval-based calculation (using time-specific factors)
2. Annual comparison calculation (using yearly average factors)

Compare the results and explain the difference."""
            
            response = self.invoke(prompt, max_tokens=max_tokens, temperature=temperature)
            reasoning_trace.append({
                'step': 'emissions_calculation',
                'decision': 'Calculate emissions using both methods',
                'explanation': response['content'],
                'tool_calls': response.get('tool_calls', [])
            })
            
            # Extract results from tool invocations
            calculation_results = self._extract_calculation_results()
            
            # Generate insights
            insights = self.generate_insights(calculation_results)
            
            logger.info("Analysis workflow completed successfully")
            
            return {
                'success': True,
                'results': calculation_results,
                'insights': insights,
                'reasoning_trace': reasoning_trace,
                'state': state,
                'filename': uploaded_file.name
            }
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'reasoning_trace': reasoning_trace,
                'message': f"Analysis failed: {str(e)}"
            }
    
    def generate_insights(
        self,
        calculation_results: Dict[str, Any]
    ) -> str:
        """
        Generate natural language insights from emissions calculation results.
        
        This method analyzes the calculation results and generates a natural language
        summary that:
        - Compares interval-based vs annual emissions
        - Identifies notable patterns and trends
        - Provides actionable recommendations
        
        Implements Requirements 0.2.3, 0.2.4, and 0.2.5.
        
        Args:
            calculation_results: Dictionary containing:
                - 'interval_total': Total interval-based emissions (tonnes)
                - 'annual_total': Total annual comparison emissions (tonnes)
                - 'percentage_diff': Percentage difference between methods
                - 'total_consumption': Total consumption (kWh)
                - 'interval_results': DataFrame with interval-level results (optional)
                - 'daily_results': DataFrame with daily aggregated results (optional)
                
        Returns:
            Natural language insights string
            
        Example:
            >>> results = {
            ...     'interval_total': 12.5,
            ...     'annual_total': 11.8,
            ...     'percentage_diff': 5.9,
            ...     'total_consumption': 15000
            ... }
            >>> insights = agent.generate_insights(results)
            >>> print(insights)
        """
        logger.info("Generating natural language insights from calculation results")
        
        # Build a prompt for the agent to generate insights
        prompt = f"""Based on the emissions calculation results, provide a comprehensive analysis with insights and recommendations.

Results:
- Total consumption: {calculation_results.get('total_consumption', 'N/A')} kWh
- Interval-based emissions: {calculation_results.get('interval_total', 'N/A')} tonnes CO2-e
- Annual average emissions: {calculation_results.get('annual_total', 'N/A')} tonnes CO2-e
- Difference: {calculation_results.get('percentage_diff', 'N/A')}%

Please provide:
1. A comparison of the two calculation methods and what the difference means
2. Notable patterns or trends in the emissions data
3. Actionable recommendations for reducing emissions

Be conversational and explain technical concepts in user-friendly terms."""
        
        try:
            response = self.invoke(prompt, max_tokens=2048, temperature=0.7)
            insights = response['content']
            
            logger.info(f"Generated insights: {len(insights)} characters")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}", exc_info=True)
            # Provide a fallback basic insight
            interval_total = calculation_results.get('interval_total') or 0
            annual_total = calculation_results.get('annual_total') or 0
            pct_diff = calculation_results.get('percentage_diff') or 0

            
            fallback = f"""Analysis Summary:

Your electricity consumption resulted in {interval_total:.2f} tonnes of CO2-equivalent emissions using the interval-based method, compared to {annual_total:.2f} tonnes using annual average factors.

The {abs(pct_diff):.1f}% difference {'higher' if pct_diff > 0 else 'lower'} with interval-based calculation reflects the time-varying nature of grid emissions intensity. This shows that the timing of your electricity use {'increases' if pct_diff > 0 else 'reduces'} your emissions impact compared to the annual average.

Consider shifting high-consumption activities to times when the grid is cleaner (typically during periods of high renewable generation) to reduce your emissions footprint."""
            
            return fallback
    
    def explain_decision(
        self,
        decision_point: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate a natural language explanation for a specific decision point in the workflow.
        
        This method provides transparency into the agent's reasoning process by explaining
        why specific decisions were made during the analysis workflow.
        
        Implements Requirements 0.5 and 0.6 (reasoning transparency).
        
        Args:
            decision_point: Name of the decision point to explain (e.g., 'interval_detection',
                          'state_selection', 'factor_matching', 'calculation_method')
            context: Dictionary with relevant context information for the decision
                    (e.g., detected values, available options, constraints)
                    
        Returns:
            Natural language explanation string
            
        Example:
            >>> context = {
            ...     'detected_interval': 5,
            ...     'max_period': 288,
            ...     'method': 'period_analysis'
            ... }
            >>> explanation = agent.explain_decision('interval_detection', context)
            >>> print(explanation)
        """
        logger.info(f"Generating explanation for decision point: {decision_point}")
        
        # Build a prompt asking the agent to explain the decision
        context_str = "\n".join([f"- {key}: {value}" for key, value in context.items()])
        
        prompt = f"""Explain the reasoning behind this decision in the emissions analysis workflow:

Decision Point: {decision_point}

Context:
{context_str}

Provide a clear, user-friendly explanation of:
1. What decision was made
2. Why this decision was made (the reasoning)
3. What alternatives were considered (if any)
4. What this means for the analysis

Keep it concise but informative."""
        
        try:
            response = self.invoke(prompt, max_tokens=1024, temperature=0.7)
            explanation = response['content']
            
            logger.info(f"Generated explanation: {len(explanation)} characters")
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating explanation: {str(e)}", exc_info=True)
            # Provide a fallback explanation
            return f"""Decision: {decision_point}

Based on the available information ({', '.join(context.keys())}), this decision was made to ensure accurate emissions calculations. The system analyzed the data characteristics and selected the most appropriate approach.

Context details: {context_str}"""
    
    def _extract_calculation_results(self) -> Dict[str, Any]:
        """
        Extract calculation results from tool invocation history.
        
        This helper method parses the tool invocation log to extract emissions
        calculation results for use in insight generation.
        
        Returns:
            Dictionary with calculation results
        """
        results = {
            'interval_total': None,
            'annual_total': None,
            'percentage_diff': None,
            'total_consumption': None
        }
        
        # Parse tool invocations to extract results
        for invocation in self.conversation.tool_invocations:
            tool_name = invocation.get('tool_name', '')
            result = invocation.get('result', {})
            
            if not result.get('success'):
                continue
            
            # Extract relevant results based on tool name
            if 'calculate_interval_emissions' in tool_name:
                tool_result = result.get('result', {})
                results['interval_total'] = tool_result.get('total_emissions_tonnes')
                results['total_consumption'] = tool_result.get('total_consumption_kwh')
                
            elif 'calculate_annual_emissions' in tool_name:
                tool_result = result.get('result', {})
                results['annual_total'] = tool_result.get('total_emissions_tonnes')
                
            elif 'calculate_percentage_difference' in tool_name:
                results['percentage_diff'] = result.get('result')
        
        return results

def create_emissions_agent(
    bedrock_mode: str = "production",
    tools: Optional[Dict[str, Callable]] = None,
    **bedrock_kwargs
) -> EmissionsAgent:
    """
    Factory function to create an EmissionsAgent with default configuration.
    
    Args:
        bedrock_mode: Operating mode ('production' or 'mock')
        tools: Optional dictionary of tools (if None, uses default tool set)
        **bedrock_kwargs: Additional arguments passed to BedrockClient
        
    Returns:
        Configured EmissionsAgent instance
        
    Example:
        >>> # Create agent in mock mode for testing
        >>> agent = create_emissions_agent(bedrock_mode='mock')
        >>> 
        >>> # Create agent in production mode with custom tools
        >>> from agents.agent_tools import tool_load_consumption_file
        >>> custom_tools = {'load_file': tool_load_consumption_file}
        >>> agent = create_emissions_agent(
        ...     bedrock_mode='production',
        ...     tools=custom_tools,
        ...     max_retries=5
        ... )
    """
    # Determine Bedrock mode
    mode = BedrockMode.PRODUCTION if bedrock_mode.lower() == 'production' else BedrockMode.MOCK
    
    # Create Bedrock client
    client = BedrockClient(mode=mode, **bedrock_kwargs)
    
    # Use provided tools or empty dict (tools can be added later)
    tool_registry = tools or {}
    
    # Create and return agent
    agent = EmissionsAgent(client, tool_registry)
    
    logger.info(
        f"Created EmissionsAgent in {mode.value} mode with {len(tool_registry)} tools"
    )
    
    return agent
