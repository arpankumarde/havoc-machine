# Havoc Machine

**Synthetic Customer Chaos Lab** - Stress-test customer support systems through AI-generated adversarial conversations that expose policy vulnerabilities, refund leakage, and chatbot weaknesses before they impact real customers.

## Problem Statement

Support operations face a critical gap between demo performance and real-world resilience. Generative AI-powered chatbots excel in controlled environments but struggle under authentic pressure scenarios including angry customers, code-mixed languages, incomplete information, and deliberate policy exploitation. Current testing methods cannot economically simulate thousands of realistic support conversations, resulting in:

- Inconsistent policy application
- Revenue leakage through exploited loopholes
- Degraded customer experiences that erode brand trust

## Features

- **AI-Generated Adversarial Conversations**: Simulate thousands of realistic support scenarios
- **Policy Vulnerability Detection**: Identify weak points in refund policies, replacement workflows, and COD return handling
- **Multi-Scenario Testing**: Test against angry customers, code-mixed languages, incomplete information, and policy exploitation attempts
- **Parallel Execution**: Run multiple adversarial sessions simultaneously for comprehensive testing
- **Real-time Dashboard**: Monitor test runs and analyze results through web interface

## Architecture

- **Server** (`server/`): FastAPI backend with LangChain, OpenAI, and MongoDB for conversation orchestration
- **Client** (`client/`): Next.js frontend with Prisma and PostgreSQL for dashboard and reporting
- **CLI** (`cli/`): Python CLI tool for running parallel adversarial red teaming sessions

## Quick Start

### Prerequisites

- Python 3.12+ (for server and CLI)
- Node.js 18+ (for client)
- PostgreSQL database
- MongoDB database
- OpenAI API key

### Configuration

Create `.env` files in respective directories with required API keys and database connection strings.

## Tech Stack

- **Backend**: FastAPI, LangChain, OpenAI, MongoDB, PostgreSQL
- **Frontend**: Next.js 16, React 19, Prisma, Tailwind CSS
- **CLI**: Python with Rich for terminal UI
