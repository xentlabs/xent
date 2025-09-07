from collections.abc import Callable
from typing import Any

from xega.common.token_xent_list import TokenXentList, round_xent
from xega.common.xega_event import (
    ElicitRequestEvent,
    ElicitResponseEvent,
    FailedEnsureEvent,
    RevealEvent,
    RewardEvent,
    XegaEvent,
)


def split_rounds(
    history: list[XegaEvent], round_marker: str = "elicit_response"
) -> list[list[XegaEvent]]:
    rounds: list[list[XegaEvent]] = []
    current_round: list[XegaEvent] = []

    for event in history:
        if event["type"] == round_marker and current_round:
            rounds.append(current_round)
            current_round = [event]
        else:
            current_round.append(event)

    if current_round:
        rounds.append(current_round)

    return rounds


def extract_rewards(events: list[XegaEvent]) -> list[RewardEvent]:
    return [event for event in events if event["type"] == "reward"]


def extract_attempts(events: list[XegaEvent]) -> list[dict[str, Any]]:
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
                attempt["failure_reason"] = (
                    f"Failed ensure at beacon {failure_event['beacon']}"
                )

            attempts.append(attempt)

    return attempts


def get_max_score(
    events: list[XegaEvent], score_fn: Callable[[RewardEvent], float] | None = None
) -> tuple[float, RewardEvent | None]:
    if score_fn is None:

        def score_fn(r):
            return r["value"].total_xent()

    rewards = extract_rewards(events)
    if not rewards:
        return 0, None

    max_reward = max(rewards, key=score_fn)
    return score_fn(max_reward), max_reward


def get_scores_by_round(history: list[XegaEvent]) -> list[dict[str, Any]]:
    rounds = split_rounds(history)
    scores_by_round = []

    for i, round_events in enumerate(rounds, 1):
        rewards = extract_rewards(round_events)
        scores = [r["value"].total_xent() for r in rewards]

        scores_by_round.append(
            {"round": i, "scores": scores, "total": sum(scores) if scores else 0}
        )

    return scores_by_round


def count_event(events: list[XegaEvent], event_type: str) -> int:
    return sum(1 for e in events if e["type"] == event_type)


def count_all_events(events: list[XegaEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        event_type_str: str = event["type"]
        counts[event_type_str] = counts.get(event_type_str, 0) + 1
    return counts


def find_round_boundaries(
    history: list[XegaEvent],
    start_event: str = "elicit_response",
    end_event: str = "reward",
) -> list[dict[str, Any]]:
    boundaries = []
    start_idx = None

    for i, event in enumerate(history):
        if event["type"] == start_event:
            start_idx = i
        elif event["type"] == end_event and start_idx is not None:
            boundaries.append(
                {
                    "start_idx": start_idx,
                    "end_idx": i,
                    "events": history[start_idx : i + 1],
                }
            )
            start_idx = None

    return boundaries


def extract_story_scores(
    events: list[XegaEvent], num_stories: int
) -> list[list[float]]:
    rounds = split_rounds(events)
    story_scores = []

    for round_events in rounds:
        rewards = extract_rewards(round_events)
        if len(rewards) >= num_stories:
            round_scores = [r["value"].total_xent() for r in rewards[:num_stories]]
            story_scores.append(round_scores)

    return story_scores


def check_word_overlap(text1: str, text2: str, ignore_case: bool = True) -> set[str]:
    if ignore_case:
        text1, text2 = text1.lower(), text2.lower()

    words1 = set(text1.split())
    words2 = set(text2.split())

    return words1.intersection(words2)


def format_token_xent_list(txl: TokenXentList) -> str:
    pairs = txl.pairs
    scale = txl.scale
    return " ".join(f"{t[0]}|{round(t[1] * scale)}" for t in pairs)


def format_reward(
    reward_event: RewardEvent, include_breakdown: bool = True
) -> tuple[str, float]:
    total = round_xent(reward_event["value"].total_xent())

    if include_breakdown:
        per_token = format_token_xent_list(reward_event["value"])
        formatted = f"Total: {total}\nPer-token: {per_token}"
    else:
        formatted = f"Total: {total}"

    return formatted, total


def format_failed_ensure(event: FailedEnsureEvent) -> str:
    results = [f"Argument {i}: {arg}" for i, arg in enumerate(event["ensure_results"])]
    results_string = ", ".join(results)
    return f"Failed ensure: {results_string}. Moving to beacon: {event['beacon']}"


def format_attempt(
    response: str, failed: bool = False, reason: str | None = None
) -> str:
    if failed:
        if reason:
            return f"<invalidAttempt>{response}</invalidAttempt> ({reason})"
        return f"<invalidAttempt>{response}</invalidAttempt>"
    return f"<attempt>{response}</attempt>"


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
    history: list[XegaEvent], initial_state: dict[str, Any] | None = None
) -> tuple[list[list[XegaEvent]], dict[str, Any]]:
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

    def add_rounds(
        self,
        rounds: list[list[XegaEvent]],
        formatter: Callable[[int, list[XegaEvent]], str] | None = None,
    ) -> "PresentationBuilder":
        for i, round_events in enumerate(rounds, 1):
            if formatter:
                self.add_line(formatter(i, round_events))
            else:
                # Default formatting
                self.start_section(f"round{i}")

                attempts = extract_attempts(round_events)
                for attempt in attempts:
                    self.add_line(
                        format_attempt(attempt["response"], attempt["failed"])
                    )

                rewards = extract_rewards(round_events)
                if rewards:
                    formatted, score = format_reward(rewards[0])
                    self.add_line(formatted)

                self.end_section()

        return self

    def add_score_breakdown(
        self, score_value: TokenXentList | float, label: str = "Score"
    ) -> "PresentationBuilder":
        if isinstance(score_value, TokenXentList):
            total = round_xent(score_value.total_xent())
            per_token = format_token_xent_list(score_value)
            self.add_line(f"{label}:")
            self.add_line(f"  Total: {total}")
            self.add_line(f"  Per-token: {per_token}")
        else:
            self.add_line(f"{label}: {score_value:.3f}")

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


def get_event_summary(history: list[XegaEvent]) -> str:
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
