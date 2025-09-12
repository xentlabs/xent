from xega.presentation.sdk import (
    PresentationBuilder,
    extract_reveals,
    extract_rewards,
    format_reward,
    split_rounds,
)


def present(state, history, metadata):
    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge"]}) to compute score.

<gameCode>
assign(s1=story(), s2=story(), s3=story())
elicit(x, 10)
assign(x1=remove_common_words(x, s1 + s2 + s3))
reveal(x1)
reward(xed(s1 | x1))
reward(xed(s2 | x1))
reward(xed(s3 | x1))
</gameCode>

You will be given three short stories, and your task is to find a single prefix that works well for ALL three stories - a prefix that helps predict each of them.

The scoring measures how much information your prefix provides about each story. For each story, your score is the difference between its baseline cross-entropy and its cross-entropy given your prefix. Your total score is the sum across all three stories: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2) - xent(story2 | prefix)] + [xent(story3) - xent(story3 | prefix)]`.

Your goal is to maximize this total score. You want to find a prefix that simultaneously helps an LLM predict all three stories - a synthesis that captures what they have in common.

After each attempt, you'll see individual scores for each story and your total score. You can play multiple rounds to continuously improve your approach. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.


You cannot use any words that appear in any of the three stories (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")

    # Extract game state
    s1 = state["s1"]
    s2 = state["s2"]
    s3 = state["s3"]

    # Present the three stories
    builder.add_line("The three stories to synthesize:")
    builder.add_line(f"<story1>{s1}</story1>")
    builder.add_line(f"<story2>{s2}</story2>")
    builder.add_line(f"<story3>{s3}</story3>")

    best_round_score = None
    rounds = split_rounds(history)

    builder.add_line("")
    builder.add_line("--- Play History ---")
    builder.add_line("")
    builder.start_section("gameHistory")

    for i in range(len(rounds) - 1):
        round_events = rounds[i]
        response = next(e for e in round_events if e["type"] == "elicit_response")[
            "response"
        ]
        prefix = extract_reveals(round_events)[0]["values"]["x1"]

        rewards = extract_rewards(round_events)

        # Render this round immediately - no manual calculation needed!
        builder.start_section(f"round{i}")
        if response == prefix:
            builder.add_line(f"<prefix>{response}</prefix>")
        else:
            builder.add_line(f"<move>{response}</move>")
            builder.add_line(f"<prefix>{prefix}</prefix>")
        builder.start_section("scores")

        total_reward = 0
        # Individual story scores - inline the rendering
        for story_num, reward in enumerate(rewards):
            builder.start_section(f"story{story_num + 1}")
            (reward_str, reward_score) = format_reward(reward)
            total_reward += reward_score
            builder.add_lines(reward_str)
            builder.end_section()

        # Total combined score - provided by SDK!
        builder.add_line(f"<totalScore>{total_reward}</totalScore>")
        if best_round_score is None or total_reward > best_round_score:
            best_round_score = total_reward
        builder.end_section()
        builder.end_section()

    # Current round marker
    builder.add_current_round_marker(len(rounds) - 1)
    builder.end_section()

    builder.add_line("")
    if best_round_score is not None:
        builder.add_line(f"Best total score achieved: {best_round_score}")
        builder.add_line(
            "Remember: You want to maximize your total score across all three stories!"
        )
        builder.add_line("")

    builder.add_line("Provide your prefix in <move></move> tags.")

    return builder.render()
