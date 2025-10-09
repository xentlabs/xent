from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    extract_attempts,
    extract_rewards,
    format_reward,
    split_rounds,
)


def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)

    b = ChatBuilder()

    # One-time header with rules and start text
    if not ctx.get("intro_sent", False):
        story = state.get("s", "")
        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s=story())
assign(s1="alpha-omega anchor angel ant apple baby beehive bird bread bull camel candle cauldron chameleon compass cornucopia crocodile dolphin elephant globe griffin helmet horse hourglass lute madonna marionette moon owl serpent sun sword thunderbolt tree walled-garden wild-man")
elicit(x, 40)
ensure(only_uses_words(s1, x))
assign(x1="Lyra bent over her Alethiometer. The dial spun to these symbols: \"" + x + "\". Lyra looked up and said \"it tells me this\":")
reward(xed(s | x1))
</gameCode>

<gameRules>
You will be given a start text `t0`. You are going to construct a sequence of 2 short texts, `t1` which follows `t0`, and `t2` which follows the concatenation `t0+t1`. `t1` must make sense and be likely to come after `t0`. `t2` must make sense and be likely to come after `t0+t1`. Your score will be how unlikely `t2` is given `t0`.

So the idea is to make a series of texts t0 t1 t2 which are each likely and predictable in sequence. But then have t2 be very unlikely when following t0.

The likelihood is judged by an LLM. If we are looking at the likelihood of a text `t1` given `t0`, we will compute that as -1 * cross-entropy(t1 | t0). So the more that `t0` helps predict `t1`, the higher the likelihood.

To determine whether `t1` and `t2` are predictable in sequence, we will use a baseline comparison of cross-entropy(" I eat food" | "After the rain"). So `t1` is valid if cross-entropy(t1 | t0) < cross-entropy(" I eat food" | "After the rain") and `t2` is valid if cross-entropy(t2 | t0+t1) < cross-entropy(" I eat food" | "After the rain").

The score is judged in the same way, so your score will be cross-entropy(t2 | t0). The more unlikely `t2` is given `t0,` the higher your score - but keep in mind the constraints of likelihood on `t1` and `t2`.

`t1` and `t2` can be at most 5 tokens long, anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored.
</gameRules>

Here is the start text `t0` for this game:
<startText>
{story}
</startText>

You will be able to play multiple rounds of this game. You will see your choices and attempts from all previous rounds. Use the history of your previous attempts to inform better choices and decisions in current play. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.

"""
        builder.add_header(header)
        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # After intro: provide concise guidance for current step
    builder = PresentationBuilder()

    # Reward summary if a previous round just completed
    last_completed_idx = None
    for i in range(len(rounds) - 2, -1, -1):  # look in earlier rounds
        if extract_rewards(rounds[i]):
            last_completed_idx = i
            break
    if last_completed_idx is not None:
        rewards = extract_rewards(rounds[last_completed_idx])
        if rewards:
            builder.start_section("reward")
            builder.add_lines(format_reward(rewards[0])[0])
            builder.end_section()
            builder.add_line("")

    # Determine current round phase
    cur_round = rounds[-1] if rounds else []
    # t1 items are from earlier lines; threshold consistent with original presentation
    first_elicit_items = [item for item in cur_round if item["line_num"] < 7]
    second_elicit_items = [item for item in cur_round if item["line_num"] >= 7]

    t1_attempts = extract_attempts(
        first_elicit_items,
        reason="Failed to beat baseline comparison for likelihood of `t1`",
    )
    t1_success = any(not a["failed"] for a in t1_attempts)

    if not t1_success:
        # If last attempt failed, show failure message
        if t1_attempts and t1_attempts[-1]["failed"]:
            builder.add_line(
                "Failed to beat baseline comparison for likelihood of `t1`."
            )
        builder.add_line("You must now attempt to set `t1`.")
        builder.add_line("Provide your move within the <move></move> tags.")
        b.user(builder.render())
        return b.render(), ctx

    # t1 accepted; handle t2
    t2_attempts = extract_attempts(
        second_elicit_items,
        reason="Failed to beat baseline comparison for likelihood of `t2`",
    )
    t2_success = any(not a["failed"] for a in t2_attempts)

    if not t2_success:
        if t2_attempts and t2_attempts[-1]["failed"]:
            builder.add_line(
                "Failed to beat baseline comparison for likelihood of `t2`."
            )
        builder.add_line("Make another move to successfully set `t2`.")
        builder.add_line("Provide your move within the <move></move> tags.")
        b.user(builder.render())
        return b.render(), ctx

    # If we reach here, both t1 and t2 were successful; next round will prompt t1 on next turn
    builder.add_line("You must now attempt to set `t1`.")
    builder.add_line("Provide your move within the <move></move> tags.")
    b.user(builder.render())
    return b.render(), ctx
