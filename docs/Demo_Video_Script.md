cat > emissions-dashboard/docs/Demo_Video_Script.md << 'EOF'
# Emissions Intelligence Agent — Demo Video Script

Organisations need to calculate electricity-related emissions accurately for reporting and decision-making. However, electricity consumption data comes in many formats and time resolutions, and emissions factors vary by region and methodology.

The Emissions Intelligence Agent is an agentic AI system that autonomously analyses raw electricity consumption data, selects the correct emissions factors, and explains each decision it makes. Rather than operating as a static dashboard, the system behaves as an intelligent agent that reasons over data and orchestrates specialist tools.

Here, an electricity consumption file is uploaded to the application. The agent immediately inspects the file structure, identifies the electricity consumption column, and detects the time resolution of the data. In this example, the agent correctly infers that the data is recorded at five-minute intervals.

In this demo, the agent is running in mock mode for speed and reliability, but it is using real emissions factors from the Australian National Electricity Market, or NEM. The NEM is the wholesale electricity market covering Australia's eastern and southern states, and its emissions factors are commonly used in Australian emissions reporting.

The emissions calculations themselves are deterministic, meaning the same input data will always produce the same numerical result. Amazon Bedrock is optional in mock mode because the core emissions calculations are handled by deterministic logic, while the language model is used only to explain what the agent did and provide insights, rather than to drive the calculations.

Based on the detected interval and selected region, the agent loads the appropriate emissions factors and calculates emissions for each time interval. It also calculates emissions using an annual average factor, allowing comparison with standard reporting approaches.

Each step of the agent's reasoning is explained in plain language, creating a transparent and repeatable audit trail that shows how the results were produced.

The Emissions Intelligence Agent demonstrates how agentic AI can transform emissions analysis from a manual calculation exercise into an intelligent, explainable workflow using AWS services.
EOF
