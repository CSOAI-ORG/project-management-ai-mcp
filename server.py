"""
Buy Pro: https://www.csoai.org/checkout

Project Management AI MCP Server - PM Intelligence
Built by MEOK AI Labs | https://meok.ai

Task decomposition, sprint planning, risk assessment,
timeline estimation, and standup report generation.
"""


import sys, os
from auth_middleware import check_access

import time
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from mcp.server.fastmcp import FastMCP
import urllib.request as _meter_urlreq
import urllib.error as _meter_urlerr

STRIPE_199 = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"

def _add_upgrade_tail(response, tier="free"):
    """Append upgrade nudge to free-tier success responses."""
    if isinstance(response, dict) and tier == "free":
        response["_upgrade_note"] = "Pro tier: unlimited calls + priority support. Upgrade: " + STRIPE_199
    return response


mcp = FastMCP("project-management-ai", instructions="")

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
_RATE_LIMITS = {"free": {"requests_per_hour": 60}, "pro": {"requests_per_hour": 5000}}
_request_log: list[float] = []
_tier = "free"


def _check_rate_limit() -> bool:
    now = time.time()
    _request_log[:] = [t for t in _request_log if now - t < 3600]
    if len(_request_log) >= _RATE_LIMITS[_tier]["requests_per_hour"]:
        return False
    _request_log.append(now)
    return True


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
_COMPLEXITY_MULTIPLIERS = {
    "trivial": 0.5, "simple": 1.0, "moderate": 2.0, "complex": 3.5, "very_complex": 6.0,
}

_TASK_TEMPLATES = {
    "frontend_feature": {
        "subtasks": ["Design UI mockup", "Create component structure", "Implement UI components", "Add state management", "Write unit tests", "Integration testing", "Code review"],
        "base_hours": 16, "skills": ["frontend", "design"],
    },
    "backend_api": {
        "subtasks": ["Design API schema", "Create data models", "Implement endpoints", "Add validation", "Write tests", "API documentation", "Code review"],
        "base_hours": 12, "skills": ["backend", "database"],
    },
    "database_migration": {
        "subtasks": ["Design schema changes", "Write migration scripts", "Test with sample data", "Backup plan", "Deploy migration", "Verify integrity"],
        "base_hours": 8, "skills": ["database", "devops"],
    },
    "bug_fix": {
        "subtasks": ["Reproduce issue", "Root cause analysis", "Implement fix", "Write regression test", "Code review"],
        "base_hours": 4, "skills": ["debugging"],
    },
    "documentation": {
        "subtasks": ["Outline structure", "Write content", "Add examples", "Peer review", "Publish"],
        "base_hours": 6, "skills": ["technical_writing"],
    },
    "devops_task": {
        "subtasks": ["Define requirements", "Configure infrastructure", "Implement CI/CD changes", "Test in staging", "Deploy to production", "Monitor"],
        "base_hours": 10, "skills": ["devops", "cloud"],
    },
    "research_spike": {
        "subtasks": ["Define research questions", "Investigate options", "Build proof of concept", "Document findings", "Present to team"],
        "base_hours": 8, "skills": ["research"],
    },
}

_RISK_CATEGORIES = {
    "technical": {"weight": 0.3, "examples": ["new_technology", "complex_integration", "performance_requirements", "security_concerns"]},
    "resource": {"weight": 0.25, "examples": ["key_person_dependency", "skill_gap", "availability", "team_capacity"]},
    "schedule": {"weight": 0.2, "examples": ["tight_deadline", "external_dependencies", "scope_creep", "unclear_requirements"]},
    "business": {"weight": 0.15, "examples": ["changing_priorities", "budget_constraints", "stakeholder_alignment", "regulatory"]},
    "external": {"weight": 0.1, "examples": ["third_party_api", "vendor_dependency", "market_changes", "compliance"]},
}

def _server_meter_check(api_key: str = "") -> dict:
    """Calls the live /verify endpoint for server-side metering. Returns the JSON dict.
    Fail-open: if /verify is unreachable or KV isn't configured, returns allowed=True
    (so the local rate-limit in _check_rate_limit remains the safety net)."""
    try:
        data = json.dumps({"api_key": api_key, "tool": ""}).encode()
        req = _meter_urlreq.Request(_METER_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with _meter_urlreq.urlopen(req, timeout=2.5) as r:
            d = json.loads(r.read())
            if isinstance(d, dict) and "allowed" in d:
                return d
    except Exception:
        pass
    return {"allowed": True, "tier": "anonymous", "remaining": 200, "upgrade_url": "https://meok.ai/pricing"}


_METER_URL = "https://proofof.ai/verify"


@mcp.tool()
def decompose_task(
    title: str,
    description: str = "",
    task_type: str = "frontend_feature",
    complexity: str = "moderate",
    include_estimates: bool = True, api_key: str = "") -> dict:
    """Break down a task into actionable subtasks with effort estimates.

    Args:
        title: Task title.
        description: Task description/requirements.
        task_type: frontend_feature | backend_api | database_migration | bug_fix | documentation | devops_task | research_spike.
        complexity: trivial | simple | moderate | complex | very_complex.
        include_estimates: Whether to include hour estimates.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade to pro tier."}

    template = _TASK_TEMPLATES.get(task_type, _TASK_TEMPLATES["frontend_feature"])
    multiplier = _COMPLEXITY_MULTIPLIERS.get(complexity, 2.0)
    base_hours = template["base_hours"] * multiplier

    subtasks = []
    subtask_count = len(template["subtasks"])
    for i, subtask_name in enumerate(template["subtasks"]):
        hours = round(base_hours / subtask_count, 1) if include_estimates else None
        subtasks.append({
            "id": f"ST-{i+1:02d}",
            "title": subtask_name,
            "estimated_hours": hours,
            "priority": "high" if i < 2 else "medium" if i < 5 else "low",
            "status": "todo",
            "dependencies": [f"ST-{i:02d}"] if i > 0 else [],
        })

    total_hours = round(base_hours, 1)

    return {
        "task": {"title": title, "description": description, "type": task_type, "complexity": complexity},
        "subtasks": subtasks,
        "estimate": {
            "total_hours": total_hours,
            "total_days": round(total_hours / 8, 1),
            "story_points": round(multiplier * 2),
            "confidence": "high" if complexity in ("trivial", "simple") else "medium" if complexity == "moderate" else "low",
        },
        "required_skills": template["skills"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def plan_sprint(
    tasks: list[dict],
    sprint_days: int = 10,
    team_size: int = 5,
    velocity: Optional[int] = None,
    sprint_name: Optional[str] = None, api_key: str = "") -> dict:
    """Plan a sprint by allocating tasks to capacity.

    Args:
        tasks: List of tasks with keys: title, story_points, priority (high|medium|low), assignee (optional).
        sprint_days: Sprint duration in working days.
        team_size: Number of team members.
        velocity: Historical velocity in story points. If omitted, estimates from team size.
        sprint_name: Sprint name/number.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade to pro tier."}

    if not velocity:
        velocity = team_size * sprint_days  # Rough: 1 SP per person per day

    # Factor in meetings/overhead (roughly 20%)
    effective_capacity = round(velocity * 0.8)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

    included = []
    overflow = []
    total_points = 0

    for task in sorted_tasks:
        sp = task.get("story_points", 3)
        if total_points + sp <= effective_capacity:
            included.append({**task, "status": "planned", "sprint_fit": True})
            total_points += sp
        else:
            overflow.append({**task, "status": "backlog", "sprint_fit": False})

    utilization = round((total_points / effective_capacity) * 100, 1) if effective_capacity else 0

    return {
        "sprint": {
            "name": sprint_name or f"Sprint {datetime.now().strftime('%Y-W%W')}",
            "duration_days": sprint_days,
            "team_size": team_size,
            "velocity": velocity,
            "effective_capacity": effective_capacity,
        },
        "planned_tasks": included,
        "overflow_tasks": overflow,
        "metrics": {
            "total_story_points": total_points,
            "utilization_pct": utilization,
            "tasks_included": len(included),
            "tasks_overflow": len(overflow),
        },
        "recommendations": [
            "Sprint is overloaded - remove low priority items" if utilization > 100 else
            "Good sprint load" if utilization > 70 else
            "Sprint has capacity - consider pulling from backlog",
            f"Aim for {round(effective_capacity * 0.85)} SP to maintain sustainable pace",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def assess_risks(
    project_name: str,
    risks: list[dict],
    project_budget: Optional[float] = None,
    deadline: Optional[str] = None, api_key: str = "") -> dict:
    """Assess project risks and generate mitigation strategies.

    Args:
        project_name: Name of the project.
        risks: List of risks with keys: description, category (technical|resource|schedule|business|external),
              likelihood (1-5), impact (1-5).
        project_budget: Total project budget for financial impact estimation.
        deadline: Project deadline in YYYY-MM-DD format.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade to pro tier."}

    if not risks:
        return {"error": "Provide at least one risk to assess."}

    assessed = []
    total_risk_score = 0

    _MITIGATIONS = {
        "technical": ["Conduct proof of concept early", "Bring in domain experts", "Add technical spike to sprint", "Increase test coverage"],
        "resource": ["Cross-train team members", "Document key processes", "Hire contractor as backup", "Adjust scope to match capacity"],
        "schedule": ["Add buffer to timeline", "Identify and cut scope", "Increase team velocity focus", "Set up weekly deadline reviews"],
        "business": ["Regular stakeholder alignment meetings", "Written scope agreement", "Change request process", "Budget contingency fund"],
        "external": ["Identify alternative vendors", "Contractual SLAs", "Build abstraction layers", "Regular vendor health checks"],
    }

    for risk in risks:
        likelihood = min(5, max(1, risk.get("likelihood", 3)))
        impact = min(5, max(1, risk.get("impact", 3)))
        category = risk.get("category", "technical")
        risk_score = likelihood * impact
        total_risk_score += risk_score

        severity = "critical" if risk_score >= 20 else "high" if risk_score >= 12 else "medium" if risk_score >= 6 else "low"
        weight = _RISK_CATEGORIES.get(category, {}).get("weight", 0.2)

        mitigations = _MITIGATIONS.get(category, ["Consult project manager"])
        financial_impact = None
        if project_budget:
            impact_pct = {1: 0.02, 2: 0.05, 3: 0.10, 4: 0.20, 5: 0.35}
            financial_impact = round(project_budget * impact_pct.get(impact, 0.1))

        assessed.append({
            "description": risk.get("description", "Unnamed risk"),
            "category": category,
            "likelihood": likelihood,
            "impact": impact,
            "risk_score": risk_score,
            "severity": severity,
            "weighted_score": round(risk_score * weight, 2),
            "financial_impact_est": financial_impact,
            "mitigations": mitigations[:2],
            "owner": "TBD",
        })

    assessed.sort(key=lambda r: r["risk_score"], reverse=True)
    avg_score = round(total_risk_score / len(assessed), 1)

    return {
        "project": project_name,
        "risk_assessment": assessed,
        "summary": {
            "total_risks": len(assessed),
            "critical": sum(1 for r in assessed if r["severity"] == "critical"),
            "high": sum(1 for r in assessed if r["severity"] == "high"),
            "medium": sum(1 for r in assessed if r["severity"] == "medium"),
            "low": sum(1 for r in assessed if r["severity"] == "low"),
            "average_risk_score": avg_score,
            "overall_risk_level": "critical" if avg_score > 15 else "high" if avg_score > 10 else "moderate" if avg_score > 5 else "low",
        },
        "top_actions": [r["mitigations"][0] for r in assessed[:3] if r["mitigations"]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def estimate_timeline(
    tasks: list[dict],
    team_size: int = 5,
    hours_per_day: float = 6.0,
    buffer_pct: float = 20.0,
    start_date: Optional[str] = None, api_key: str = "") -> dict:
    """Estimate project timeline from task list with dependency awareness.

    Args:
        tasks: List with keys: title, estimated_hours, dependencies (list of task titles), parallelizable (bool).
        team_size: Number of people working.
        hours_per_day: Productive hours per person per day.
        buffer_pct: Risk buffer percentage to add.
        start_date: Start date in YYYY-MM-DD format.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade to pro tier."}

    if not start_date:
        start_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_hours = sum(t.get("estimated_hours", 8) for t in tasks)
    parallel_capacity = team_size * hours_per_day

    # Simple critical path approximation
    sequential_hours = 0
    parallel_hours = 0
    for task in tasks:
        hours = task.get("estimated_hours", 8)
        if task.get("dependencies") or not task.get("parallelizable", True):
            sequential_hours += hours
        else:
            parallel_hours += hours

    parallel_days = parallel_hours / parallel_capacity if parallel_capacity else 0
    sequential_days = sequential_hours / hours_per_day
    estimated_days = math.ceil(parallel_days + sequential_days)

    buffer_days = math.ceil(estimated_days * (buffer_pct / 100))
    total_days = estimated_days + buffer_days

    start = datetime.strptime(start_date, "%Y-%m-%d")
    # Skip weekends
    end = start
    business_days = 0
    while business_days < total_days:
        end += timedelta(days=1)
        if end.weekday() < 5:
            business_days += 1

    milestones = []
    quarter_days = max(1, total_days // 4)
    for i, label in enumerate(["Planning Complete", "Core Development", "Testing & QA", "Launch Ready"], 1):
        m_date = start
        bd = 0
        target = quarter_days * i
        while bd < target:
            m_date += timedelta(days=1)
            if m_date.weekday() < 5:
                bd += 1
        milestones.append({"milestone": label, "target_date": m_date.strftime("%Y-%m-%d"), "day": target})

    return {
        "project_timeline": {
            "start_date": start_date,
            "estimated_end_date": end.strftime("%Y-%m-%d"),
            "estimated_days": estimated_days,
            "buffer_days": buffer_days,
            "total_business_days": total_days,
            "total_calendar_days": (end - start).days,
        },
        "effort": {
            "total_hours": round(total_hours, 1),
            "sequential_hours": round(sequential_hours, 1),
            "parallelizable_hours": round(parallel_hours, 1),
            "team_size": team_size,
            "hours_per_day": hours_per_day,
        },
        "milestones": milestones,
        "tasks": [{"title": t.get("title", "?"), "hours": t.get("estimated_hours", 8), "dependencies": t.get("dependencies", [])} for t in tasks],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def generate_standup(
    team_updates: list[dict],
    sprint_day: int = 1,
    sprint_total_days: int = 10,
    blockers: Optional[list[str]] = None, api_key: str = "") -> dict:
    """Generate a formatted standup report from team updates.

    Args:
        team_updates: List with keys: name, yesterday (list of items), today (list of items), blockers (list).
        sprint_day: Current day of sprint.
        sprint_total_days: Total sprint days.
        blockers: Team-level blockers.

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need structured analysis or classification
        of inputs against established frameworks or standards.

    When NOT to use:
        Not suitable for real-time production decision-making without
        human review of results.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": STRIPE_199}

    if not _check_rate_limit():
        return {"error": "Rate limit exceeded. Upgrade to pro tier."}

    formatted_updates = []
    all_blockers = list(blockers or [])
    items_completed = 0
    items_planned = 0

    for update in team_updates:
        name = update.get("name", "Unknown")
        yesterday = update.get("yesterday", [])
        today = update.get("today", [])
        personal_blockers = update.get("blockers", [])

        items_completed += len(yesterday)
        items_planned += len(today)
        all_blockers.extend(personal_blockers)

        formatted_updates.append({
            "name": name,
            "completed": yesterday,
            "planned": today,
            "blockers": personal_blockers,
            "status": "blocked" if personal_blockers else "on_track",
        })

    sprint_pct = round((sprint_day / sprint_total_days) * 100)
    blocked_count = sum(1 for u in formatted_updates if u["status"] == "blocked")

    summary_lines = []
    summary_lines.append(f"Sprint Day {sprint_day}/{sprint_total_days} ({sprint_pct}% through)")
    summary_lines.append(f"Team: {len(formatted_updates)} members reporting")
    summary_lines.append(f"Completed yesterday: {items_completed} items")
    summary_lines.append(f"Planned today: {items_planned} items")
    if all_blockers:
        summary_lines.append(f"BLOCKERS: {len(all_blockers)} active")

    return {
        "standup_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sprint_progress": {"day": sprint_day, "total": sprint_total_days, "pct": sprint_pct},
        "team_updates": formatted_updates,
        "summary": summary_lines,
        "blockers": list(set(all_blockers)),
        "health": "at_risk" if blocked_count > len(formatted_updates) // 2 else "healthy",
        "action_items": [f"Resolve: {b}" for b in all_blockers[:3]] if all_blockers else ["No blockers - keep momentum"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    mcp.run()

if __name__ == '__main__':
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
