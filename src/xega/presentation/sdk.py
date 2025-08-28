from typing import Any

from xega.common.token_xent_list import round_xent
from xega.common.xega_event import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    RevealEvent,
    RewardEvent,
    XegaEvent,
)


def format_reveal(event: RevealEvent) -> str:
    """Convert reveal event to readable format"""
    values_str = str(
        [f'{arg}: "{str(event["values"][arg])}"' for arg in event["values"]]
    )
    return f"{event['line_num']:02d}-<reveal>: {values_str}"


def format_elicit_request(event: ElicitRequestEvent) -> str:
    """Format elicit request for agent"""
    return f"{event['line_num']:02d}-<elicit>: {event['var_name']} (max {event['max_len']} tokens)"


def format_elicit_response(event: ElicitResponseEvent) -> str:
    """Format elicit response"""
    return f"{event['line_num']:02d}-<elicit response>: {event['response']}"


def format_reward(event: RewardEvent) -> str:
    """Format reward event"""
    total_reward = round_xent(event["value"].total_xent())
    per_token_rewards = str(event["value"])
    return f"{event['line_num']:02d}-<reward>: Total reward: {total_reward}, per-token rewards: {per_token_rewards}"


def format_failed_ensure(event: FailedEnsureEvent) -> str:
    """Format failed ensure event"""
    results = [
        f"Argument {i} result: {arg}" for i, arg in enumerate(event["ensure_results"])
    ]
    results_string = ", ".join(results)
    return f"{event['line_num']:02d}-<ensure>: Failed ensure. {results_string}. Moving code execution to beacon: {event['beacon']}"


def get_event_summary(history: list[XegaEvent]) -> str:
    """Get a summary of the game history"""
    event_counts: dict[str, int] = {}
    for event in history:
        event_type: str = event["type"]  # Cast to str to avoid mypy issue
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    summary_parts = []
    for event_type, count in event_counts.items():
        summary_parts.append(f"{count} {event_type}")

    return "Game history: " + ", ".join(summary_parts)


def get_current_registers(state: dict[str, Any]) -> dict[str, str]:
    """Extract current register values from game state"""
    registers = {}
    for name, value in state.items():
        if hasattr(value, "primary_string"):  # XString objects
            registers[name] = str(value.primary_string)
        elif isinstance(value, str | int | float | bool):
            registers[name] = str(value)
    return registers


def format_registers_display(registers: dict[str, str]) -> str:
    """Format register values for display"""
    if not registers:
        return "No registers available"

    register_lines = []
    for name, value in registers.items():
        register_lines.append(f"  {name}: {value}")

    return "Current registers:\n" + "\n".join(register_lines)
