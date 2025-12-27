#!/bin/bash

# Havoc Machine CLI Runner
# This script makes it easy to run the CLI using uv

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed."
    echo "Please install uv from https://github.com/astral-sh/uv"
    exit 1
fi

# Run the CLI using uv
echo "Starting Havoc Machine CLI..."
echo ""

uv run havoc-cli "$@"

