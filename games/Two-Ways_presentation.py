from xega.presentation.sdk import (
    PresentationBuilder,
    extract_rewards,
    format_token_xent_list,
    split_rounds,
)


def present(state, history, metadata):
    # Extract game state
    story_a = state["s1"]
    story_c = state["s2"]

    # Build presentation
    builder = PresentationBuilder()

    # Game header
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

    # Split history into rounds
    rounds = split_rounds(history)

    # Track best score
    best_score = None

    # Show game history if any completed rounds exist
    if rounds and any(extract_rewards(r) for r in rounds):
        builder.add_line("")
        builder.start_section("gameHistory")

        for i, round_events in enumerate(rounds):
            rewards = extract_rewards(round_events)
            if rewards and len(rewards) >= 2:  # Only show completed rounds with scores
                render_complete_round(round_events, builder, i + 1)

                # Track best score (first two rewards only)
                total_score = (
                    rewards[0]["value"].total_xent() + rewards[1]["value"].total_xent()
                )
                if best_score is None or total_score > best_score:
                    best_score = total_score

        builder.end_section()

    # Show current game status
    builder.add_line("")
    builder.add_line("Current game status:")
    builder.add_line(f"<storyA>{story_a}</storyA>")
    builder.add_line(f"<storyC>{story_c}</storyC>")
    builder.add_line("")
    builder.add_line(
        'Your goal: Create a bridge text B that makes both "A→B→C" and "C→B→A" flow naturally.'
    )

    if best_score is not None:
        builder.add_line(f"Best score so far: {best_score:.3f}")

    builder.add_line("")
    builder.add_line("Provide your bridge text in <move></move> tags.")

    return builder.render()


def render_complete_round(round_events, builder, round_num):
    # Extract the response (bridge text)
    response_event = next(
        (e for e in round_events if e["type"] == "elicit_response"), None
    )

    if not response_event:
        return

    # Get rewards (only first two are actual scores)
    rewards = extract_rewards(round_events)
    if len(rewards) < 2:
        return

    builder.start_section(f"round{round_num}")

    # Show the bridge text
    builder.add_line(f"<bridge>{response_event['response']}</bridge>")

    # Score ABC (first reward)
    abc_reward = rewards[0]
    abc_score = abc_reward["value"].total_xent()
    builder.start_section("scoreABC")
    builder.add_line(f"Total: {abc_score:.3f}")
    builder.add_line(f"Per-token: {format_token_xent_list(abc_reward['value'])}")
    builder.end_section()

    # Score CBA (second reward)
    cba_reward = rewards[1]
    cba_score = cba_reward["value"].total_xent()
    builder.start_section("scoreCBA")
    builder.add_line(f"Total: {cba_score:.3f}")
    builder.add_line(f"Per-token: {format_token_xent_list(cba_reward['value'])}")
    builder.end_section()

    # Combined total
    total_score = abc_score + cba_score
    builder.add_line(f"<totalScore>{total_score:.3f}</totalScore>")

    builder.end_section()
