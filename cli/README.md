# Havoc Machine CLI

A powerful command-line interface for running parallel adversarial red teaming sessions, similar to the web UI but with full terminal control.

## Features

- 🚀 Start multiple parallel adversarial sessions
- 📊 Real-time monitoring with split terminal windows (one per session)
- 🔄 Automatic polling of session messages
- 📝 View JSON logs and reports directly in nano
- ⌨️ Full keyboard control with menu-driven interface

## Installation

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Bash shell

### Setup

1. Navigate to the CLI directory:
```bash
cd cli
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Unix/Mac
# or
.venv\Scripts\activate  # On Windows
```

## Usage

### Quick Start

Run the CLI using the provided bash script:

```bash
./run.sh
```

Or run directly with uv:

```bash
uv run havoc-cli
```

### Configuration

When you start the CLI, you'll be prompted for:

1. **WebSocket URL** (default: `ws://localhost:8000`)
   - The WebSocket URL for the agent server
   - Automatically converts to HTTP base URL for API calls

2. **Number of Sessions** (default: `3`)
   - How many parallel adversarial sessions to run

3. **Duration** (default: `2` minutes)
   - How long each session should run

### During Execution

Once started, the CLI will:

1. Show session IDs and progress
2. Split the terminal into horizontal windows (one per session)
3. Automatically poll and display messages from each session
4. Show real-time updates every 6 seconds

### After Completion

When sessions complete, you'll see:

- S3 URLs for the report and JSON logs
- A menu-driven interface with options:
  - **J**: View JSON logs (downloads and opens in nano)
  - **R**: View Report (downloads and opens in nano)
  - **Q**: Quit

### Keyboard Controls

- **Q**: Quit the application (at any time)
- **J**: Open JSON logs in nano (after completion)
- **R**: Open Report in nano (after completion)

## API Endpoints Used

The CLI interacts with the following server endpoints:

- `POST /api/adversarial/parallel` - Start parallel adversarial sessions
- `GET /api/session/{session_id}/messages` - Poll messages for a session
- `GET /api/groups/{group_id}` - Get group metadata (optional)

## Architecture

```
cli/
├── havoc_cli/
│   ├── __init__.py      # Package initialization
│   ├── main.py          # Main entry point and orchestration
│   ├── api_client.py    # API client for server communication
│   └── ui.py            # Terminal UI components
├── pyproject.toml       # Project configuration and dependencies
├── run.sh               # Convenience script to run the CLI
└── README.md            # This file
```

## Dependencies

- `rich` - Beautiful terminal UI and formatting
- `requests` - HTTP client for API calls
- `inquirer` - Interactive command-line prompts

## Troubleshooting

### Server Connection Issues

If you get connection errors, make sure:
- The server is running on the specified port
- The WebSocket URL is correct
- The server is accessible from your machine

### Terminal Display Issues

If the terminal windows don't display correctly:
- Make sure your terminal is large enough (at least 120x40 characters)
- Try resizing your terminal window
- The UI adapts to terminal size automatically

### Keyboard Input Not Working

On some systems, keyboard input may not work in the live view. In that case:
- Wait for sessions to complete
- Use the menu options after completion
- Or restart the CLI

## Development

To develop or modify the CLI:

1. Make your changes to the source files
2. Install in development mode:
```bash
uv pip install -e .
```

3. Run with:
```bash
uv run havoc-cli
```

## License

Same as the main Havoc Machine project.

