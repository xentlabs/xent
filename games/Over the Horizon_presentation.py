from xega.presentation.sdk import (
    PresentationBuilder,
    extract_attempts,
    extract_rewards,
    format_attempt,
    format_reward,
    split_rounds,
)


def present(state, history):
    story = state["s"]

    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = f"""You are playing a game.

<gameRules>
You will be given a start text `t0`. You are going to construct a sequence of 2 short texts, `t1` which follows `t0`, and `t2` which follows the concatenation `t0+t1`. `t1` must make sense and be likely to come after `t0`. `t2` must make sense and be likely to come after `t0+t1`. Your score will be how unlikely `t2` is given `t0`.

So the idea is to make a series of texts t0 t1 t2 which are each likely and predictable in sequence. But then have t2 be very unlikely when following t0.

The likelyhood is judged by an LLM. If we are looking at the likelyhood of a text `t1` given `t0`, we will compute that as -1 * cross-entropy(t1 | t0). So the more that `t0` helps predict `t1`, the higher the likelyhood.

To determine whether `t1` and `t2` are predictable in sequence, we will use a baseline comparison of cross-entropy(" I eat food" | "After the rain"). So `t1` is valid if cross-entropy(t1 | t0) < cross-entropy(" I eat food" | "After the rain") and `t2` is valid if cross-entropy(t2 | t0+t1) < cross-entropy(" I eat food" | "After the rain").

The score is judged in the same way, so your score will be cross-entropy(t2 | t0). The more unlikely `t2` is given `t0,` the higher your score - but keep in mind the constraints of likelihood on `t1` and `t2`.

`t1` and `t2` can be at most 5 tokens long, anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored.
</gameRules>

Here is the start text `t0` for this game:
<startText>
{story}
</startText>

You will be able to play multiple rounds of this game. You will see your choices and attempts from all previous rounds. Use the history of your previous attempts to inform better choices and decisions in current play.
"""

    builder.add_header(header)
    rounds = split_rounds(history)

    builder.add_line("A history of your play so far:")
    builder.add_line("")
    builder.start_section("fullHistory")

    for i in range(len(rounds) - 1):
        round = rounds[i]
        builder.start_section(f"round_{i}")
        render_complete_round(round, builder)
        builder.end_section()

    builder.start_section(f"round_{len(rounds) - 1}")
    render_current_round(rounds[-1], builder)
    builder.end_section()
    builder.end_section()

    builder.add_line("")
    builder.add_line("Now provide your next move within the <move></move> tags.")

    return builder.render()


def render_complete_round(round, builder):
    first_elicit_items = [item for item in round if item["line_num"] < 7]
    first_elicit_attempts = extract_attempts(
        first_elicit_items,
        reason="Failed to beat baseline comparison for likelyhood of `t1`",
    )
    builder.start_section("t1_selection")
    for attempt in first_elicit_attempts:
        builder.add_line(format_attempt(**attempt))
    builder.end_section()

    builder.start_section("t2_selection")
    second_elicit_items = [item for item in round if item["line_num"] >= 7]
    second_elicit_attempts = extract_attempts(
        second_elicit_items,
        reason="Failed to beat baseline comparison for likelyhood of `t2`",
    )
    for attempt in second_elicit_attempts:
        builder.add_line(format_attempt(**attempt))
    builder.end_section()

    reward = extract_rewards(round)[0]
    builder.start_section("reward")
    builder.add_line(format_reward(reward)[0])
    builder.end_section()


def render_current_round(round, builder):
    first_elicit_items = [item for item in round if item["line_num"] < 7]
    first_elicit_attempts = extract_attempts(
        first_elicit_items,
        reason="Failed to beat baseline comparison for likelyhood of `t1`",
    )
    builder.start_section("t1_selection")
    success = False
    for attempt in first_elicit_attempts:
        if not attempt["failed"]:
            success = True
        builder.add_line(format_attempt(**attempt))

    if not success:
        builder.add_line("You are HERE. You must now attempt to set `t1`")
        builder.end_section()
        return

    builder.end_section()
    builder.start_section("t2_selection")

    second_elicit_items = [item for item in round if item["line_num"] >= 7]
    second_elicit_attempts = extract_attempts(
        second_elicit_items,
        reason="Failed to beat baseline comparison for likelyhood of `t2`",
    )
    for attempt in second_elicit_attempts:
        builder.add_line(format_attempt(**attempt))

    builder.add_line("You are HERE. Make another move to successfully set `t2`")
    builder.end_section()
