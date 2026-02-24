# Use Case Document: Emissions Intelligence Agent

## Executive Summary

The Emissions Intelligence Agent is an agentic AI system that autonomously analyzes electricity consumption data and produces transparent, explainable emissions calculations. This document outlines the problem statement, solution architecture, target users, and the agentic behaviors that differentiate this system from traditional static dashboards.

---

## Problem Statement

Organizations are increasingly required to measure, understand, and report electricity-related emissions for compliance, sustainability reporting, and decarbonization planning. However, electricity consumption data varies widely in:

- **Structure**: Different column names, formats, and data layouts
- **Time Resolution**: 5-minute vs 30-minute intervals
- **File Formats**: CSV, XLSX, and other formats
- **Regional Factors**: Emissions factors differ by region, interval, and reporting methodology

### Current Challenges

Today, emissions calculations are often:
- **Manual**: Requiring significant analyst time and effort
- **Opaque**: Lacking transparency in methodology and assumptions
- **Error-Prone**: Susceptible to human error and inconsistencies
- **Difficult to Audit**: Making it hard for analysts, sustainability teams, and auditors to trust results or understand underlying assumptions

---

## Solution Overview

The **Emissions Intelligence Agent** is an agentic AI system that autonomously analyzes raw electricity consumption data and produces transparent, explainable emissions calculations. 

### Key Differentiator

Rather than operating as a static dashboard, the system behaves as an **intelligent agent** that:
- Reasons over data
- Orchestrates specialist tools
- Explains its decisions at each step

### Core Workflow

1. **Data Ingestion**: The agent ingests consumption data uploaded by a user
2. **Structure Inference**: Infers the data structure and time interval
3. **Factor Selection**: Selects the appropriate regional emissions factors
4. **Dual Calculation**: Calculates emissions using both:
   - Interval-based methodology (time-specific factors)
   - Annual-average methodology (comparison baseline)
5. **Transparent Reasoning**: Exposes its reasoning and decisions in natural language, providing a clear audit trail

---

## Target Users

### Primary Users
- **Sustainability and ESG Teams**: Organizations tracking and reporting emissions
- **Energy and Emissions Analysts**: Professionals performing detailed emissions analysis
- **Compliance Teams**: Organizations subject to emissions reporting obligations
- **Consultants and Auditors**: Third parties validating emissions calculations

### User Benefits
- Reduced manual effort in emissions calculations
- Increased confidence in reporting accuracy
- Clear audit trail for compliance
- Transparent methodology for stakeholder communication

---

## Agentic Behaviour

The system demonstrates **agentic AI** through autonomous, multi-step reasoning and tool orchestration:

### 1. Data Ingestion & Understanding
The agent loads CSV or Excel consumption files and validates their structure.

**Autonomous Actions**:
- File format detection
- Data structure validation
- Column identification

### 2. Inference & Decision-Making
It autonomously identifies the electricity consumption column and detects the recording interval.

**Autonomous Actions**:
- Pattern recognition in column names
- Interval detection (5-minute or 30-minute data)
- Data quality assessment

### 3. Contextual Tool Selection
Based on detected interval and user-selected region, the agent selects the correct emissions factor datasets.

**Autonomous Actions**:
- Regional factor selection (NSW, VIC, QLD, SA, TAS)
- Interval-specific factor matching
- Data alignment and validation

### 4. Autonomous Execution
The agent executes interval-based emissions calculations and parallel annual-average calculations for comparison.

**Autonomous Actions**:
- Dual methodology calculation
- Percentage difference analysis
- Results validation

### 5. Explainability & Transparency
Each decision and calculation step is explained in plain language, enabling traceability and audit readiness.

**Autonomous Actions**:
- Natural language reasoning trace
- Tool invocation logging
- Decision explanation generation

---

## Technical Architecture

The solution is built using AWS services and agentic design patterns:

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **User Interface** | Streamlit | Interactive agent control and observability interface |
| **AI Reasoning** | Amazon Bedrock | Large language model reasoning and agent orchestration |
| **Agent Tools** | Python Modules | File I/O, data validation, interval detection, factor selection, emissions calculation |
| **Data Storage** | Amazon S3 | Emissions factor data storage and management |
| **Local Mode** | Mock Agent | Deterministic calculations for development and testing |

### Agentic Design Pattern

The agent coordinates tools through a **structured reasoning workflow** rather than a fixed script, enabling:
- **Flexibility**: Adapts to different data formats and structures
- **Extensibility**: New tools can be added without rewriting core logic
- **Transparency**: Each step is logged and explainable
- **Reliability**: Fallback mechanisms for error handling

### Data Flow