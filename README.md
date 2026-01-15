# Price_Alert

Polymarket price alert system - A tool that monitors Polymarket prices and sends alerts.

## Quick Start

1. **Read CLAUDE.md first** - Contains essential rules for Claude Code
2. Follow the pre-task compliance checklist before starting any work
3. Use proper module structure under `src/main/python/`
4. Commit after every completed task

## Project Structure

```
Price_Alert/
├── CLAUDE.md              # Essential rules for Claude Code
├── README.md              # Project documentation
├── .gitignore             # Git ignore patterns
├── src/                   # Source code
│   ├── main/              # Main application code
│   │   ├── python/        # Python code
│   │   │   ├── core/      # Core business logic
│   │   │   ├── utils/     # Utility functions
│   │   │   ├── models/    # Data models
│   │   │   ├── services/  # Service layer
│   │   │   └── api/       # API endpoints/interfaces
│   │   └── resources/     # Non-code resources
│   │       ├── config/    # Configuration files
│   │       └── assets/    # Static assets
│   └── test/              # Test code
│       ├── unit/          # Unit tests
│       └── integration/   # Integration tests
├── docs/                  # Documentation
├── tools/                 # Development tools
├── examples/              # Usage examples
└── output/                # Generated output files
```

## Development Guidelines

- **Always search first** before creating new files
- **Extend existing** functionality rather than duplicating
- **Use Task agents** for operations >30 seconds
- **Single source of truth** for all functionality
- **Commit frequently** after each completed feature

## Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the price alert system
python -m src.main.python.core.main
```

## License

MIT
