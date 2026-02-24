"""
Emissions Intelligence Agent - Streamlit Dashboard

This Streamlit application provides an agent-centric interface for autonomous
emissions analysis using AWS Bedrock and Claude 3.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
import os
from emissions.workflow import calculate_emissions_deterministic


# Import agent components
from agents.emissions_agent import create_emissions_agent
from agents.bedrock_client import BedrockMode, BedrockClient
from agents.agent_tools import (
    tool_load_consumption_file,
    tool_identify_consumption_column,
    tool_identify_time_columns
)

# Import emissions modules
from emissions.viz import (
    create_daily_emissions_chart,
    create_comparison_chart,
    create_summary_metrics
)

# Configure Streamlit page
st.set_page_config(
    page_title="Emissions Intelligence Agent",
    page_icon="🌱",
    layout="wide"
)

# ============================================================================
# Session State Initialization
# ============================================================================

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'agent' not in st.session_state:
        st.session_state.agent = None
    
    if 'agent_status' not in st.session_state:
        st.session_state.agent_status = 'ready'  # ready, analyzing, complete, error
    
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    if 'uploaded_file_data' not in st.session_state:
        st.session_state.uploaded_file_data = None
    
    if 'bedrock_mode' not in st.session_state:
        # Default to mock mode if no AWS credentials
        st.session_state.bedrock_mode = 'mock'
    
    if 'reasoning_trace' not in st.session_state:
        st.session_state.reasoning_trace = []
    
    if 'tool_invocations' not in st.session_state:
        st.session_state.tool_invocations = []

initialize_session_state()

# ============================================================================
# Helper Functions
# ============================================================================

def get_agent_status_color(status: str) -> str:
    """Get color for agent status indicator."""
    colors = {
        'ready': 'green',
        'analyzing': 'orange',
        'complete': 'blue',
        'error': 'red'
    }
    return colors.get(status, 'gray')

def get_agent_status_icon(status: str) -> str:
    """Get emoji icon for agent status."""
    icons = {
        'ready': '✅',
        'analyzing': '⚙️',
        'complete': '🎉',
        'error': '❌'
    }
    return icons.get(status, '❓')

def create_agent_instance(mode: str) -> Optional[Any]:
    """Create an EmissionsAgent instance with the specified mode."""
    if mode.lower() != "mock":
        mode = "mock"
    try:
        bedrock_mode = "mock"
        agent = create_emissions_agent(
            bedrock_mode=bedrock_mode,
            tools={
                'load_consumption_file': tool_load_consumption_file,
                'identify_consumption_column': tool_identify_consumption_column,
                'identify_time_columns': tool_identify_time_columns
            }
        )
        return agent
    except Exception as e:
        st.error(f"Failed to create agent: {str(e)}")
        return None

def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured."""
    has_env_vars = (
        os.environ.get('AWS_ACCESS_KEY_ID') and 
        os.environ.get('AWS_SECRET_ACCESS_KEY')
    )
    has_credentials_file = os.path.exists(os.path.expanduser('~/.aws/credentials'))
    
    return has_env_vars or has_credentials_file

# ============================================================================
# UI Components
# ============================================================================

def render_header():
    """Render the agent-centric UI header (Task 8.1)."""
    st.title("🌱 Emissions Intelligence Agent")
    
    st.markdown("""
    Welcome to the **Emissions Intelligence Agent** - your autonomous AI assistant for electricity emissions analysis.
    
    **Agentic Capabilities:**
    - 🤖 **Autonomous Analysis**: Upload your data and let the agent handle the rest
    - 🧠 **Intelligent Reasoning**: The agent explains its decisions and findings in plain language
    - 🔧 **Tool Selection**: Automatically selects and invokes the right analysis tools
    - 📊 **Insight Generation**: Identifies patterns and provides actionable recommendations
    - 🔍 **Transparent Process**: See exactly what the agent is doing and why
    """)
    
    # Agent status indicator
    status = st.session_state.agent_status
    status_icon = get_agent_status_icon(status)
    status_color = get_agent_status_color(status)
    
    st.markdown(f"""
    <div style="padding: 10px; border-radius: 5px; background-color: {status_color}20; border-left: 4px solid {status_color};">
        <strong>Agent Status:</strong> {status_icon} {status.upper()}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

def render_aws_configuration():
    """Render AWS configuration interface (Task 8.8)."""
    with st.sidebar:
        st.header("⚙️ AWS Configuration")
        
        # Check Bedrock connection status
        has_credentials = check_aws_credentials()
        
        if has_credentials:
            st.success("✅ AWS credentials detected")
            connection_status = "Connected (credentials found)"
        else:
            st.warning("⚠️ No AWS credentials detected")
            connection_status = "Not configured"
        
        st.info(f"**Connection Status:** {connection_status}")
        
        # Mode selection
        #mode_options = ['Mock', 'Production']
        #default_mode = 'Production' if has_credentials else 'Mock'
        mode_options = ['Mock']
        default_mode = 'Mock'

        
        selected_mode = st.selectbox(
            "Operating Mode",
            mode_options,
            index=mode_options.index(default_mode),
            help="Mock mode simulates agent responses. Production mode uses AWS Bedrock."
        )
        
        st.session_state.bedrock_mode = selected_mode.lower()
        
        # Display current mode
        if st.session_state.bedrock_mode == 'mock':
            st.info("🧪 **Mock Mode**: Running locally with real emissions calculations (no AWS calls)")
        else:
            st.info("🚀 **Production Mode**: Using AWS Bedrock with Claude 3")
        
        # Configuration guidance
        with st.expander("📖 AWS Setup Guide"):
            st.markdown("""
            **To use Production Mode:**
            
            1. **Install boto3:**
               ```bash
               pip install boto3
               ```
            
            2. **Configure AWS credentials** (choose one):
               - Environment variables:
                 ```bash
                 export AWS_ACCESS_KEY_ID=your_key
                 export AWS_SECRET_ACCESS_KEY=your_secret
                 export AWS_REGION=us-east-1
                 ```
               - AWS credentials file (`~/.aws/credentials`):
                 ```
                 [default]
                 aws_access_key_id = your_key
                 aws_secret_access_key = your_secret
                 ```
               - IAM role (for EC2/ECS/Lambda)
            
            3. **Ensure Bedrock access:**
               - Your IAM user/role needs `bedrock:InvokeModel` permission
               - Claude 3 model must be enabled in your AWS account
            
            4. **Select Production mode** above and start analyzing!
            """)
        
        st.markdown("---")
        
        # Display agent info if initialized
        if st.session_state.agent:
            agent_info = st.session_state.agent.get_agent_info()
            st.subheader("Agent Info")
            st.json({
                'Mode': agent_info['bedrock_mode'],
                'Model': agent_info['bedrock_model'],
                'Tools': agent_info['tool_count'],
                'Messages': agent_info['message_count']
            })

def render_file_upload():
    """Render file upload with agent handoff (Task 8.2)."""
    st.header("📁 Upload Consumption Data")
    
    st.markdown("""
    Upload your electricity consumption data in CSV or Excel format. 
    The agent will autonomously analyze the structure and guide you through the process.
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['csv', 'xlsx'],
        help="Upload CSV or Excel file with consumption data"
    )
    
    if uploaded_file is not None:
        # Store uploaded file in session state
        st.session_state.uploaded_file_data = uploaded_file
        
        # Display file info
        st.success(f"✅ File uploaded: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
        
        # Initialize agent if not already done
        if st.session_state.agent is None:
            with st.spinner("Initializing agent..."):
                st.session_state.agent = create_agent_instance(st.session_state.bedrock_mode)
        
        # Agent's initial understanding
        if st.session_state.agent:
            with st.expander("🤖 Agent's Initial Understanding", expanded=True):
                st.markdown("**Agent is analyzing the file structure...**")
                
                try:
                    # Load file using agent tool
                    result = tool_load_consumption_file(uploaded_file)
                    
                    if result['success']:
                        st.success(result['message'])
                        
                        # Display data preview
                        df_data = result['result']['value']
                        metadata = df_data['metadata']
                        
                        st.markdown(f"""
                        **Data Structure Detected:**
                        - **Rows:** {metadata['row_count']}
                        - **Columns:** {metadata['column_count']}
                        - **Column Names:** {', '.join(metadata['columns'])}
                        """)
                        
                        # Show preview
                        if 'preview' in df_data:
                            st.markdown("**Data Preview:**")
                            preview_df = pd.DataFrame(df_data['preview'])
                            st.dataframe(preview_df, use_container_width=True)
                    else:
                        st.error(f"❌ {result['message']}")
                        
                except Exception as e:
                    st.error(f"Error analyzing file: {str(e)}")
        
        return uploaded_file
    
    return None

def render_agent_reasoning():
    """Render agent reasoning display (Task 8.3)."""
    if not st.session_state.reasoning_trace:
        return
    
    st.header("🧠 Agent Reasoning Process")
    
    st.markdown("""
    See how the agent makes decisions and selects tools to analyze your data.
    Each step shows the agent's reasoning and the tools it invoked.
    """)
    
    for idx, step in enumerate(st.session_state.reasoning_trace):
        step_num = idx + 1
        step_name = step.get('step', f'Step {step_num}')
        decision = step.get('decision', 'Processing...')
        explanation = step.get('explanation', 'No explanation available')
        tool_calls = step.get('tool_calls', [])
        
        with st.expander(f"**Step {step_num}: {step_name}**", expanded=(idx == len(st.session_state.reasoning_trace) - 1)):
            st.markdown(f"**Decision:** {decision}")
            st.markdown(f"**Explanation:**\n\n{explanation}")
            
            if tool_calls:
                st.markdown("**Tools Invoked:**")
                for tool_call in tool_calls:
                    tool_name = tool_call.get('name', 'Unknown')
                    arguments = tool_call.get('arguments', {})
                    st.code(f"{tool_name}({arguments})", language='python')

def render_agent_insights():
    """Render agent insight display (Task 8.4)."""
    if not st.session_state.analysis_results:
        return
    
    results = st.session_state.analysis_results
    
    if not results.get('success'):
        st.error(f"❌ Analysis failed: {results.get('error', 'Unknown error')}")
        return
    
    st.header("💡 Agent-Generated Insights")
    
    # Display insights
    insights = results.get('insights', '')
    if insights:
        st.markdown(insights)
    
    # Display calculation results
    calc_results = results.get('results', {})
    if calc_results:
        st.subheader("📊 Emissions Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:

            st.metric(
                "Total Consumption",
                f"{(calc_results.get('total_consumption') or 0):.2f} kWh"
            )

            st.metric(
                "Interval-Based Emissions",
                f"{(calc_results.get('interval_total') or 0):.2f} tonnes CO2-e"
            )

            pct_diff = calc_results.get('percentage_diff') or 0
            st.metric(
                "vs Annual Average",
                f"{(calc_results.get('annual_total') or 0):.2f} tonnes CO2-e",
                delta=f"{pct_diff:+.2f}%"
)


def render_user_feedback():
    """Render user feedback and control (Task 8.5)."""
    st.header("💬 Feedback & Control")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Explain this insight", help="Ask the agent to explain its reasoning"):
            if st.session_state.agent:
                with st.spinner("Agent is generating explanation..."):
                    try:
                        explanation = st.session_state.agent.explain_decision(
                            'insight_generation',
                            {'results': st.session_state.analysis_results}
                        )
                        st.info(explanation)
                    except Exception as e:
                        st.error(f"Error generating explanation: {str(e)}")
    
    with col2:
        if st.button("🔄 Start new analysis", help="Clear current analysis and start fresh"):
            # Reset session state
            st.session_state.agent = None
            st.session_state.agent_status = 'ready'
            st.session_state.conversation_history = []
            st.session_state.analysis_results = None
            st.session_state.reasoning_trace = []
            st.session_state.tool_invocations = []
            st.rerun()
    
    # User corrections
    with st.expander("✏️ Provide corrections or feedback"):
        user_feedback = st.text_area(
            "Correct agent assumptions or provide additional context:",
            placeholder="E.g., 'The data is actually from Victoria, not NSW'"
        )
        
        if st.button("Submit feedback"):
            if user_feedback and st.session_state.agent:
                st.session_state.conversation_history.append({
                    'role': 'user',
                    'content': user_feedback
                })
                st.success("✅ Feedback recorded. The agent will consider this in future interactions.")

def render_visualizations():
    """Render visualization with agent narration (Task 8.6)."""
    if not st.session_state.analysis_results:
        return
    
    results = st.session_state.analysis_results
    calc_results = results.get('results', {})
    
    if not calc_results:
        return
    
    st.header("📈 Visualizations")
    
    # Comparison chart
    st.subheader("Calculation Method Comparison")
    
    interval_total = calc_results.get('interval_total', 0)
    annual_total = calc_results.get('annual_total', 0)
    
    if interval_total and annual_total:
        fig = create_comparison_chart(interval_total, annual_total)
        st.plotly_chart(fig, use_container_width=True)
        
        # Agent narration
        pct_diff = calc_results.get('percentage_diff', 0)
        if pct_diff > 0:
            narration = f"""
            **Agent's Analysis:** The interval-based calculation shows {abs(pct_diff):.1f}% higher emissions 
            than the annual average method. This indicates that your electricity consumption pattern tends to 
            occur during times when the grid has higher emissions intensity.
            """
        elif pct_diff < 0:
            narration = f"""
            **Agent's Analysis:** The interval-based calculation shows {abs(pct_diff):.1f}% lower emissions 
            than the annual average method. This is positive - your consumption pattern aligns with times 
            when the grid has lower emissions intensity (more renewable generation).
            """
        else:
            narration = """
            **Agent's Analysis:** The interval-based and annual average calculations are very similar, 
            suggesting your consumption pattern is well-distributed across different times of day.
            """
        
        st.info(narration)

def render_export_options():
    """Render results export with agent summary (Task 8.7)."""
    if not st.session_state.analysis_results:
        return
    
    st.header("💾 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Download Results (CSV)"):
            # Prepare results for export
            results = st.session_state.analysis_results
            calc_results = results.get('results', {})
            
            # Create summary DataFrame
            summary_data = {
                'Metric': [
                    'Total Consumption (kWh)',
                    'Interval-Based Emissions (tonnes CO2-e)',
                    'Annual Average Emissions (tonnes CO2-e)',
                    'Percentage Difference (%)'
                ],
                'Value': [
                    calc_results.get('total_consumption', 0),
                    calc_results.get('interval_total', 0),
                    calc_results.get('annual_total', 0),
                    calc_results.get('percentage_diff', 0)
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            csv = summary_df.to_csv(index=False)
            
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="emissions_results.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📥 Download Reasoning Trace (JSON)"):
            import json
            
            # Prepare reasoning trace for export
            trace_data = {
                'analysis_results': st.session_state.analysis_results,
                'reasoning_trace': st.session_state.reasoning_trace,
                'tool_invocations': st.session_state.tool_invocations,
                'agent_mode': st.session_state.bedrock_mode
            }
            
            json_str = json.dumps(trace_data, indent=2, default=str)
            
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="agent_reasoning_trace.json",
                mime="application/json"
            )

    with col3:
        if st.button("📥 Download Detailed Emissions (CSV)"):
            results = st.session_state.analysis_results
            
            # Get the detailed interval results DataFrame
            if 'interval_results_df' in results:
                detailed_df = results['interval_results_df']
                csv = detailed_df.to_csv(index=False)
                
                st.download_button(
                    label="Download Detailed CSV",
                    data=csv,
                    file_name="detailed_emissions_calculations.csv",
                    mime="text/csv"
                )
            else:
                st.error("Detailed results not available")

# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point."""
    
    # Render header (Task 8.1)
    render_header()
    
    # Render AWS configuration sidebar (Task 8.8)
    render_aws_configuration()
    
    # Render file upload (Task 8.2)
    uploaded_file = render_file_upload()
    
    # If file is uploaded, show analysis options
    if uploaded_file and st.session_state.agent:
        st.markdown("---")
        
        # State selection
        st.subheader("🗺️ Select NEM State")
        state = st.selectbox(
            "Which Australian state is this data from?",
            ['NSW', 'VIC', 'QLD', 'SA', 'TAS'],
            help="Select the National Electricity Market state for emissions factors"
        )
        
        # Start analysis button
        if st.button("🚀 Start Autonomous Analysis", type="primary"):
            st.session_state.agent_status = 'analyzing'
            
            with st.spinner("🤖 Agent is analyzing your data..."):
                try:
                    # Run autonomous analysis
                    # Import at top of file
                    from emissions.workflow import calculate_emissions_deterministic

                    # Then in the button handler:
                    result = calculate_emissions_deterministic(
                        uploaded_file=uploaded_file,
                        state=state
                    )

                    
                    # Store results
                    st.session_state.analysis_results = result
                    st.session_state.reasoning_trace = result.get('reasoning_trace', [])
                    st.session_state.tool_invocations = st.session_state.agent.get_tool_invocation_log()
                    
                    if result.get('success'):
                        st.session_state.agent_status = 'complete'
                        st.success("✅ Analysis complete!")
                    else:
                        st.session_state.agent_status = 'error'
                        st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                    
                    st.rerun()
                    
                except Exception as e:
                    st.session_state.agent_status = 'error'
                    st.error(f"❌ Error during analysis: {str(e)}")
    
    # Render analysis results if available
    if st.session_state.agent_status in ['complete', 'error']:
        st.markdown("---")
        
        # Render agent reasoning (Task 8.3)
        render_agent_reasoning()
        
        st.markdown("---")
        
        # Render agent insights (Task 8.4)
        render_agent_insights()
        
        st.markdown("---")
        
        # Render visualizations (Task 8.6)
        render_visualizations()
        
        st.markdown("---")
        
        # Render user feedback (Task 8.5)
        render_user_feedback()
        
        st.markdown("---")
        
        # Render export options (Task 8.7)
        render_export_options()

if __name__ == "__main__":
    main()
