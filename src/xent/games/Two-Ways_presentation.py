from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    extract_rewards,
    format_token_xent_list,
    split_rounds,
)


def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)

    b = ChatBuilder()

    # One-time introduction and current status
    if not ctx.get("intro_sent", False):
        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s1=story(), s2=story())
assign(s="I have a fun story to tell you:")
elicit(t, 10)
reward(nex(s2 | s + s1 + t))
reward(nex(s1 | s + s2 + t))
reward(xent(s2 | s + s1))
reward(xent(s1 | s + s2))
</gameCode>

In this game you are given 2 short texts A and C. Your goal is to create a bridge text B such that the text ABC makes sense and CBA also makes sense.

The scoring will be computed using the cross entropy of C given AB plus the cross entropy of A given CB. Specifically `-1 * (crossEntropy(C | AB) + crossEntropy(A | CB))`. So the more likely you can make the text in both directions, the higher your score will be.

Your goal is to optimize your score. So try to provide bridge text B (max 10 tokens) such that A→B→C flows naturally and C→B→A also flows naturally.

You will have multiple attempts to improve your score. After each attempt, you will be given the per-token cross entropy of the scored text. Use this information to improve your score on the next round. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.


Your move can only be 10 tokens long in total. Anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored."""

        builder.add_header(header)
        builder.add_line("")

        story_a = state.get("s1", "")
        story_c = state.get("s2", "")
        builder.add_line("Current game status:")
        builder.add_line(f"<storyA>{story_a}</storyA>")
        builder.add_line(f"<storyC>{story_c}</storyC>")
        builder.add_line("")
        builder.add_line(
            'Your goal: Create a bridge text B that makes both "A→B→C" and "C→B→A" flow naturally.'
        )
        builder.add_line("")
        builder.add_line("Provide your bridge text in <move></move> tags.")

        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # Subsequent turns: summarize latest completed round and prompt
    builder = PresentationBuilder()

    # Identify the most recent completed round (needs at least 2 rewards)
    last_completed_index = None
    for i in range(len(rounds) - 1, -1, -1):
        rewards = extract_rewards(rounds[i])
        if len(rewards) >= 2:
            last_completed_index = i
            break

    # Compute best score so far
    best_score = None
    for i in range(len(rounds)):
        rewards = extract_rewards(rounds[i])
        if len(rewards) >= 2:
            abc = rewards[0]["value"].total_xent()
            cba = rewards[1]["value"].total_xent()
            total = abc + cba
            if best_score is None or total > best_score:
                best_score = total

    if last_completed_index is not None:
        round_events = rounds[last_completed_index]
        rewards = extract_rewards(round_events)
        builder.add_line(f"Round {last_completed_index}:")

        # Scores for ABC and CBA, total
        abc_reward = rewards[0]
        abc_score = abc_reward["value"].total_xent()
        builder.start_section("scoreABC")
        builder.add_line(f"Total: {abc_score:.3f}")
        builder.add_line(f"Per-token: {format_token_xent_list(abc_reward['value'])}")
        builder.end_section()

        cba_reward = rewards[1]
        cba_score = cba_reward["value"].total_xent()
        builder.start_section("scoreCBA")
        builder.add_line(f"Total: {cba_score:.3f}")
        builder.add_line(f"Per-token: {format_token_xent_list(cba_reward['value'])}")
        builder.end_section()

        total_score = abc_score + cba_score
        builder.add_line(f"<totalScore>{total_score:.3f}</totalScore>")
        builder.add_line("")

    if best_score is not None:
        builder.add_line(f"Best score so far: {best_score:.3f}")

    builder.add_line("")
    builder.add_line("Provide your bridge text in <move></move> tags.")

    b.user(builder.render())
    return b.render(), ctx
