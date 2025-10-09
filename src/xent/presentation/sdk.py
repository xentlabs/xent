from collections.abc import Callable
from typing import Any

from xent.common.token_xent_list import TokenXentList
from xent.common.xent_event import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    LLMMessage,
    LLMRole,
    RevealEvent,
    RewardEvent,
    XentEvent,
)

PRESENTATION_SCORE_SCALE = 10


def round_xent(value: float, scaled: bool = True) -> float:
    if scaled:
        return round(value * PRESENTATION_SCORE_SCALE)
    return round(value)


def split_rounds(history: list[XentEvent]) -> list[list[XentEvent]]:
    rounds: list[list[XentEvent]] = []
    current_round: list[XentEvent] = []

    for event in history:
        if event["type"] == "round_started":
            current_round = [event]
        elif event["type"] == "round_finished":
            current_round.append(event)
            rounds.append(current_round)
            current_round = []
        else:
            current_round.append(event)

    if len(current_round) > 0:
        rounds.append(current_round)

    return rounds


def extract_rewards(events: list[XentEvent]) -> list[RewardEvent]:
    return [event for event in events if event["type"] == "reward"]


def extract_reveals(events: list[XentEvent]) -> list[RevealEvent]:
    return [event for event in events if event["type"] == "reveal"]


def extract_attempts(events: list[XentEvent], reason: str = "") -> list[dict[str, Any]]:
    attempts = []

    for i, event in enumerate(events):
        if event["type"] == "elicit_response":
            attempt = {
                "response": event["response"],
                "failed": False,
                "failure_reason": None,
            }

            # Check if next event is a failure
            if i + 1 < len(events) and events[i + 1]["type"] == "failed_ensure":
                attempt["failed"] = True
                failure_event: FailedEnsureEvent = events[i + 1]  # type: ignore
                failure_reason = (
                    reason
                    if reason
                    else f"Failed ensure at beacon {failure_event['beacon']}"
                )
                attempt["failure_reason"] = failure_reason

            attempts.append(attempt)

    return attempts


def get_max_score(
    events: list[XentEvent],
    scaled: bool = True,
    score_fn: Callable[[RewardEvent], float] | None = None,
) -> tuple[float, RewardEvent | None]:
    if score_fn is None:

        def _score_fn(r):
            val = r["value"].total_xent()
            if scaled:
                val = val * PRESENTATION_SCORE_SCALE
            return val

        score_fn = _score_fn

    rewards = extract_rewards(events)
    if not rewards:
        return 0, None

    max_reward = max(rewards, key=score_fn)
    return score_fn(max_reward), max_reward


def get_scores_by_round(history: list[XentEvent]) -> list[dict[str, Any]]:
    rounds = split_rounds(history)
    scores_by_round = []

    for i, round_events in enumerate(rounds):
        rewards = extract_rewards(round_events)
        scores = [r["value"].total_xent() for r in rewards]

        scores_by_round.append(
            {"round": i, "scores": scores, "total": sum(scores) if scores else 0}
        )

    return scores_by_round


def count_event(events: list[XentEvent], event_type: str) -> int:
    return sum(1 for e in events if e["type"] == event_type)


def count_all_events(events: list[XentEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type_str: str = event["type"]
        counts[event_type_str] = counts.get(event_type_str, 0) + 1
    return counts


def format_token_xent_list(txl: TokenXentList, scaled: bool = True) -> str:
    pairs = txl.pairs
    scale = txl.scale * (PRESENTATION_SCORE_SCALE if scaled else 1)
    return " ".join(f"{t[0]}|{round(t[1] * scale)}" for t in pairs)


def format_reward(
    reward_event: RewardEvent, include_breakdown: bool = True, scaled: bool = True
) -> tuple[str, float]:
    total = round_xent(reward_event["value"].total_xent(), scaled=scaled)

    if include_breakdown:
        per_token = format_token_xent_list(reward_event["value"], scaled=scaled)
        formatted = f"Total: {total}\nPer-token: {per_token}"
    else:
        formatted = f"Total: {total}"

    return formatted, total


def format_failed_ensure(event: FailedEnsureEvent) -> str:
    results = [f"Argument {i}: {arg}" for i, arg in enumerate(event["ensure_results"])]
    results_string = ", ".join(results)
    return f"Failed ensure: {results_string}. Moving to beacon: {event['beacon']}"


def format_attempt(
    response: str, failed: bool = False, failure_reason: str | None = None
) -> str:
    if failed:
        if failure_reason:
            return f"<invalidMove>{response}</invalidMove> ({failure_reason})"
        return f"<invalidMove>{response}</invalidMove>"
    return f"<move>{response}</move>"


def format_score_comparison(
    current: float, best: float, improve_verb: str = "maximize"
) -> str:
    if current >= best:
        return f"New best score: {current:.3f} (previous best: {best:.3f})"
    else:
        gap = best - current if improve_verb == "maximize" else current - best
        return f"Score: {current:.3f} (best: {best:.3f}, gap: {gap:.3f})"


def format_round_summary(
    round_num: int, attempts: list[dict[str, Any]], score: float | None = None
) -> str:
    lines = [f"Round {round_num}:"]

    failed = [a for a in attempts if a["failed"]]
    if failed:
        lines.append(f"  Failed attempts: {len(failed)}")

    successful = [a for a in attempts if not a["failed"]]
    if successful:
        lines.append(f"  Successful: {successful[-1]['response']}")

    if score is not None:
        lines.append(f"  Score: {score:.3f}")

    return "\n".join(lines)


def format_reveal(event: RevealEvent) -> str:
    values_str = ", ".join(
        f'{arg}: "{str(event["values"][arg])}"' for arg in event["values"]
    )
    return f"Revealed: {values_str}"


def format_elicit_request(event: ElicitRequestEvent) -> str:
    return f"Request: {event['var_name']} (max {event['max_len']} tokens)"


def format_elicit_response(event: ElicitResponseEvent) -> str:
    return f"Response: {event['response']}"


def process_rounds_with_state(
    history: list[XentEvent], initial_state: dict[str, Any] | None = None
) -> tuple[list[list[XentEvent]], dict[str, Any]]:
    if initial_state is None:
        initial_state = {}

    state = initial_state.copy()
    rounds = split_rounds(history)

    # Track best score across rounds
    all_rewards = extract_rewards(history)
    if all_rewards:
        best_score, _ = get_max_score(history)
        state["best_score"] = best_score

    # Track total attempts
    state["total_attempts"] = count_event(history, "elicit_response")
    state["successful_rounds"] = len([r for r in rounds if extract_rewards(r)])

    return rounds, state


class PresentationBuilder:
    def __init__(self):
        self.sections: list[str] = []
        self.section_stack: list[tuple[str, dict[str, Any]]] = []
        self.current_indent = 0

    def add_header(self, text: str) -> "PresentationBuilder":
        self.sections.append(text)
        return self

    def add_line(self, text: str, indent: int | None = None) -> "PresentationBuilder":
        if indent is None:
            indent = self.current_indent

        indented = "  " * indent + text if indent > 0 else text
        self.sections.append(indented)
        return self

    def add_lines(self, text: str, indent: int | None = None) -> "PresentationBuilder":
        for line in text.splitlines():
            self.add_line(line, indent)
        return self

    def start_section(self, tag: str, **attrs: Any) -> "PresentationBuilder":
        self.section_stack.append((tag, attrs))

        if attrs:
            attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
            self.add_line(f"<{tag} {attr_str}>")
        else:
            self.add_line(f"<{tag}>")

        self.current_indent += 1
        return self

    def end_section(self) -> "PresentationBuilder":
        if not self.section_stack:
            return self

        tag, _ = self.section_stack.pop()
        self.current_indent = max(0, self.current_indent - 1)
        self.add_line(f"</{tag}>")
        return self

    def add_game_state(self, **state_vars: Any) -> "PresentationBuilder":
        for name, value in state_vars.items():
            if isinstance(value, str) and "\n" not in value:
                self.add_line(f"<{name}>{value}</{name}>")
            else:
                self.start_section(name)
                self.add_line(str(value))
                self.end_section()

        return self

    def add_current_round_marker(self, round_num: int) -> "PresentationBuilder":
        self.start_section(f"round{round_num}")
        self.add_line("<current/>")
        self.end_section()
        return self

    def render(self, separator: str = "\n") -> str:
        # Close any unclosed sections
        while self.section_stack:
            self.end_section()

        return separator.join(self.sections)


def get_event_summary(history: list[XentEvent]) -> str:
    event_counts = count_all_events(history)
    summary_parts = [
        f"{count} {event_type}" for event_type, count in event_counts.items()
    ]
    return "Game history: " + ", ".join(summary_parts)


def get_current_registers(state: dict[str, Any]) -> dict[str, str]:
    registers = {}
    for name, value in state.items():
        if hasattr(value, "primary_string"):  # XString objects
            registers[name] = str(value.primary_string)
        elif isinstance(value, str | int | float | bool):
            registers[name] = str(value)
    return registers


def format_registers_display(registers: dict[str, str]) -> str:
    if not registers:
        return "No registers available"

    register_lines = []
    for name, value in registers.items():
        register_lines.append(f"  {name}: {value}")

    return "Current registers:\n" + "\n".join(register_lines)


class ChatBuilder:
    """
    Lightweight helper to build append-only chat messages for LLMs.

    Typical usage in a presentation function:

        b = ChatBuilder()
        b.system("Game rules…")
        b.user("Round summary…")
        return b.render()

    Notes:
    - Presentations should generally emit only 'system' or 'user' messages.
    - Assistant messages are typically produced by the model and appended by the runtime.
    """

    def __init__(self) -> None:
        self._messages: list[LLMMessage] = []

    def add(self, role: LLMRole, content: str) -> "ChatBuilder":
        # Basic guard to avoid empty content spam
        if content is None or str(content).strip() == "":
            return self
        self._messages.append({"role": role, "content": str(content)})
        return self

    def system(self, content: str) -> "ChatBuilder":
        return self.add("system", content)

    def user(self, content: str) -> "ChatBuilder":
        return self.add("user", content)

    def assistant(self, content: str) -> "ChatBuilder":
        # Exposed for completeness; generally not used by presentations
        return self.add("assistant", content)

    def extend(self, messages: list[LLMMessage]) -> "ChatBuilder":
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            self.add(str(role), str(content))  # type: ignore[arg-type]
        return self

    def render(self) -> list[LLMMessage]:
        return list(self._messages)
