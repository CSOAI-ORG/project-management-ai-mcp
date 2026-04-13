# Project Management AI MCP Server

**PM Intelligence**

Built by [MEOK AI Labs](https://meok.ai)

---

An MCP server for project managers and agile teams. Decompose tasks with effort estimates, plan sprints against team velocity, assess project risks with STRIDE-style analysis, estimate timelines with buffer calculations, and generate formatted standup reports.

## Tools

| Tool | Description |
|------|-------------|
| `decompose_task` | Break down tasks into subtasks with hour estimates and story points |
| `plan_sprint` | Plan sprints by allocating tasks to team capacity with overflow handling |
| `assess_risks` | Risk assessment with severity scoring and mitigation strategies |
| `estimate_timeline` | Timeline estimation with critical path and milestone planning |
| `generate_standup` | Generate formatted standup reports from team updates |

## Quick Start

```bash
pip install project-management-ai-mcp
```

### Claude Desktop

```json
{
  "mcpServers": {
    "project-management-ai": {
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "/path/to/project-management-ai-mcp"
    }
  }
}
```

### Direct Usage

```bash
python server.py
```

## Rate Limits

| Tier | Requests/Hour |
|------|--------------|
| Free | 60 |
| Pro | 5,000 |

## License

MIT - see [LICENSE](LICENSE)

---

*Part of the MEOK AI Labs MCP Marketplace*
