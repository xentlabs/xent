from xega.presentation.sdk import (
    PresentationBuilder,
    extract_rewards,
    format_token_xent_list,
    get_scores_by_round,
    split_rounds,
)


def present(state, history):
    # Extract game state
    s1 = state["s1"]
    s2 = state["s2"]
    s3 = state["s3"]

    # Get structured score data using SDK
    scores_by_round = get_scores_by_round(history)
    best_total_score = max((r["total"] for r in scores_by_round), default=None)

    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = """You are playing a multi-text synthesis game. You will be given three short stories, and your task is to find a single prefix that works well for ALL three stories - a prefix that helps predict each of them.

The scoring measures how much information your prefix provides about each story. For each story, your score is the difference between its baseline cross-entropy and its cross-entropy given your prefix. Your total score is the sum across all three stories: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2) - xent(story2 | prefix)] + [xent(story3) - xent(story3 | prefix)]`.

Your goal is to MAXIMIZE this total score. You want to find a prefix that simultaneously helps an LLM predict all three stories - a synthesis that captures what they have in common.

After each attempt, you'll see individual scores for each story and your total score. You can play multiple rounds to continuously improve your approach.

You cannot use any words that appear in any of the three stories (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")

    # Present the three stories
    builder.add_line("The three stories to synthesize:")
    builder.add_line(f"<story1>{s1}</story1>")
    builder.add_line(f"<story2>{s2}</story2>")
    builder.add_line(f"<story3>{s3}</story3>")

    # Process history and build output in single pass
    if not scores_by_round:
        builder.add_line("")
        builder.add_line("Round 1 starting.")
    else:
        builder.add_line("")
        builder.add_line("--- Play History ---")
        builder.add_line("")
        builder.start_section("gameHistory")

        # Get rounds for response extraction
        rounds = split_rounds(history)

        # Process each completed round and render immediately
        for i, score_data in enumerate(scores_by_round):
            if (
                len(score_data["scores"]) >= 3
            ):  # Only show complete rounds with all 3 stories
                # Get the response for this round
                round_events = rounds[i]
                response_event = next(
                    e for e in round_events if e["type"] == "elicit_response"
                )
                rewards = extract_rewards(round_events)

                # Render this round immediately - no manual calculation needed!
                builder.start_section(f"round{score_data['round']}")
                builder.add_line(f"<prefix>{response_event['response']}</prefix>")
                builder.start_section("scores")

                # Individual story scores - inline the rendering
                for story_num, (score, reward) in enumerate(
                    zip(score_data["scores"][:3], rewards[:3], strict=False), 1
                ):
                    builder.start_section(f"story{story_num}")
                    builder.add_line(f"Total: {score:.3f}")
                    builder.add_line(
                        f"Per-token: {format_token_xent_list(reward['value'])}"
                    )
                    builder.end_section()

                # Total combined score - provided by SDK!
                builder.add_line(f"<totalScore>{score_data['total']:.3f}</totalScore>")
                builder.end_section()
                builder.end_section()

        # Current round marker
        builder.add_current_round_marker(len(scores_by_round) + 1)
        builder.end_section()

        builder.add_line("")
        if best_total_score is not None:
            builder.add_line(f"Best total score achieved: {best_total_score:.3f}")
            builder.add_line(
                "Remember: You want to MAXIMIZE your total score across all three stories!"
            )
        builder.add_line("")

    builder.add_line("Provide your prefix in <move></move> tags.")

    return builder.render()
