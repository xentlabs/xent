from xega.presentation.sdk import (
    PresentationBuilder,
    extract_rewards,
    format_token_xent_list,
    get_scores_by_round,
    split_rounds,
)


def present(state, history):
    # Extract game state
    story_a = state["s1"]
    story_c = state["s2"]

    # Get structured score data using SDK
    scores_by_round = get_scores_by_round(history)
    # This game uses negative scoring (lower is better), so find minimum
    best_total = min((r["total"] for r in scores_by_round), default=None)

    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = """You are playing a game. In this game you are given 2 short texts A and C. Your goal is to create a bridge text B such that the text ABC makes sense and CBA also makes sense.

The scoring will be computed using the cross entropy of C given AB plus the cross entropy of A given CB. Specifically `-1 * (crossEntropy(C | AB) + crossEntropy(A | CB))`. So the more likely you can make the text in both directions, the higher your score will be.

Your goal is to optimize your score. So try to provide bridge text B (max 10 tokens) such that A→B→C flows naturally and C→B→A also flows naturally.

You will have multiple attempts to improve your score. After each attempt, you will be given the per-token cross entropy of the scored text. Use this information to improve your score on the next round.

Your move can only be 10 tokens long in total. Anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")
    builder.add_line(f"<storyA>{story_a}</storyA>")
    builder.add_line(f"<storyC>{story_c}</storyC>")
    builder.add_line("")
    builder.add_line("--- Play History ---")
    builder.add_line("")

    # Process history and build output in single pass
    if not scores_by_round:
        builder.add_line("Round 1 starting.")
    else:
        builder.start_section("gameHistory")

        # Get rounds for response extraction
        rounds = split_rounds(history)

        # Process each completed round and render immediately
        for i, score_data in enumerate(scores_by_round):
            if len(score_data["scores"]) >= 2:  # Need both ABC and CBA scores
                # Get the response (bridge text) for this round
                round_events = rounds[i]
                response_event = next(
                    e for e in round_events if e["type"] == "elicit_response"
                )
                rewards = extract_rewards(round_events)

                # Render this round immediately
                builder.start_section(f"round{score_data['round']}")
                builder.add_line(f"<bridge>{response_event['response']}</bridge>")

                # Score ABC with per-token breakdown
                abc_score = score_data["scores"][0]
                builder.start_section("scoreABC")
                builder.add_line(f"Total: {abc_score:.3f}")
                builder.add_line(
                    f"Per-token: {format_token_xent_list(rewards[0]['value'])}"
                )
                builder.end_section()

                # Score CBA with per-token breakdown
                cba_score = score_data["scores"][1]
                builder.start_section("scoreCBA")
                builder.add_line(f"Total: {cba_score:.3f}")
                builder.add_line(
                    f"Per-token: {format_token_xent_list(rewards[1]['value'])}"
                )
                builder.end_section()

                # Combined total - provided by SDK!
                builder.add_line(
                    f"<combinedTotal>{score_data['total']:.3f}</combinedTotal>"
                )
                builder.end_section()

        # Current round marker
        builder.add_current_round_marker(len(scores_by_round) + 1)
        builder.end_section()

        builder.add_line("")
        if best_total is not None:
            builder.add_line(f"Best total: {best_total:.3f}")
        builder.add_line("")

    builder.add_line("Provide your bridge text in <move></move> tags.")

    return builder.render()
