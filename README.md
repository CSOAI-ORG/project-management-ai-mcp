<div align="center">

# Project Management Ai MCP

**Project Management AI MCP Server - PM Intelligence**

[![PyPI](https://img.shields.io/pypi/v/meok-project-management-ai-mcp)](https://pypi.org/project/meok-project-management-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Project Management AI MCP Server - PM Intelligence
Built by MEOK AI Labs | https://meok.ai

Task decomposition, sprint planning, risk assessment,
timeline estimation, and standup report generation.

## Tools

| Tool | Description |
|------|-------------|
| `decompose_task` | Break down a task into actionable subtasks with effort estimates. |
| `plan_sprint` | Plan a sprint by allocating tasks to capacity. |
| `assess_risks` | Assess project risks and generate mitigation strategies. |
| `estimate_timeline` | Estimate project timeline from task list with dependency awareness. |
| `generate_standup` | Generate a formatted standup report from team updates. |

## Installation

```bash
pip install meok-project-management-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "project-management-ai": {
      "command": "python",
      "args": ["-m", "meok_project_management_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 5 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
