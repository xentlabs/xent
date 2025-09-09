from xega.presentation.sdk import (
    PresentationBuilder,
    extract_reveals,
    extract_rewards,
    format_reward,
    split_rounds,
)


def present(state, history):
    # Extract game state
    s1 = state["s1"]
    s2 = state["s2"]

    # Parse history and track best score
    rounds = split_rounds(history)
    best_contrast_score = None
    completed_round_count = 0

    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = """You are playing a contrast game. You will be given two short stories, and your task is to find a prefix that creates maximum contrast between them - a prefix that helps predict the first story while making the second story LESS predictable.

The scoring measures this contrast effect:
- For story 1: Your score measures how much your prefix helps predict it (higher = better)
- For story 2: Your score measures how much your prefix makes it diverge from expectations (higher = better contrast)
- Combined score: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2 | prefix) - xent(story2)]`

Your goal is to maximize this total score. You want a prefix that simultaneously helps predict story 1 while making story 2 surprising - creating maximum contrast between the two stories.

After each attempt, you'll see individual scores showing how well you're helping story 1 and hindering story 2, plus your combined contrast score. You can play multiple rounds to continuously improve your approach.

You cannot use any words that appear in either story (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")

    # Present the two stories
    builder.add_line("The two stories to contrast:")
    builder.add_line(f"Make this predictable: <story1>{s1}</story1>")
    builder.add_line(f"Make this surprising: <story2>{s2}</story2>")

    if len(rounds) == 1:
        builder.add_line("")
        builder.add_line("Round 1 starting.")
    else:
        builder.add_line("")
        builder.add_line("--- Play History ---")
        builder.add_line("")
        builder.start_section("gameHistory")

        for round_num in range(len(rounds) - 1):
            round_events = rounds[round_num]
            rewards = extract_rewards(round_events)
            completed_round_count += 1

            # Get the response for this round
            response = next(e for e in round_events if e["type"] == "elicit_response")[
                "response"
            ]
            prefix = extract_reveals(round_events)[0]["values"]["x1"]

            # Calculate scores
            (story1_score_str, story1_score) = format_reward(rewards[0])
            (story2_score_str, story2_score) = format_reward(rewards[1])
            contrast_score = round(story1_score + story2_score, 3)

            # Track best score
            if best_contrast_score is None or contrast_score > best_contrast_score:
                best_contrast_score = contrast_score

            # Render this round immediately
            builder.start_section(f"round{round_num}")
            if response == prefix:
                builder.add_line(f"<prefix>{response}</prefix>")
            else:
                builder.add_line(f"<move>{response}</move>")
                builder.add_line(f"<prefix>{prefix}</prefix>")
            builder.start_section("scores")

            # Story 1 score (predictability boost)
            builder.start_section("story1_predictability")
            builder.add_lines(story1_score_str)
            builder.end_section()

            # Story 2 score (surprise factor)
            builder.start_section("story2_surprise")
            builder.add_lines(story2_score_str)
            builder.end_section()

            # Combined contrast score
            builder.add_line(f"<contrastScore>{contrast_score}</contrastScore>")
            builder.end_section()
            builder.end_section()

        # Current round marker
        builder.add_current_round_marker(completed_round_count)
        builder.end_section()

        builder.add_line("")
        if best_contrast_score is not None:
            builder.add_line(f"Best contrast score achieved: {best_contrast_score}")
            builder.add_line(
                "Remember: maximize your score by helping story 1 while hindering story 2!"
            )
        builder.add_line("")

    builder.add_line("Provide your prefix in <move></move> tags.")

    return builder.render()
