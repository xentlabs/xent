from xega.presentation.sdk import (
    PresentationBuilder,
    extract_attempts,
    extract_reveals,
    extract_rewards,
    format_reward,
    get_max_score,
    split_rounds,
)


def present(state, history):
    # Extract data using SDK utilities
    rounds = split_rounds(history)
    all_rewards = extract_rewards(history)
    best_score, _ = get_max_score(all_rewards) if all_rewards else (None, None)

    # Calculate current round number
    round_number = len(rounds) - 1

    # Build presentation using the builder
    builder = PresentationBuilder()

    # Game header
    header = """You are playing a text game that uses the cross-entropy function of an LLM (Qwen3-14B-Base) to compute score.

<gameCode>
assign(s=story())
elicit(x, 10)
assign(x1=remove_common_words(x, s))
reveal(x1)
reward(xed(s | x1))
</gameCode>

You will be given a short story, and your task is to provide a prefix that makes that story as predictable as possible. Think of it as providing context that helps predict what comes next.

The scoring measures how much information your prefix provides about the story. Specifically, your score is the difference between the story's baseline cross-entropy and its cross-entropy given your prefix: `Score = crossEntropy(story) - crossEntropy(story | prefix)`. Your goal is to maximize this score. So you want to find a prefix that will most help an LLM predict the story.

After each attempt, you'll see your score and a per-token breakdown of the cross entropy difference. The game automatically restarts after each successful attempt, allowing you to continuously optimize your approach. Use the feedback from previous rounds to improve your score.

You cannot use any words that appear in the story itself (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")

    # Current story
    builder.add_line("The story:")
    builder.start_section("story")
    builder.add_line(str(state["s"]))
    builder.end_section()

    # Game history
    if len(rounds) == 1:
        builder.add_line("First round starting.")
    else:
        builder.start_section("gameHistory")

        # Process each completed round
        for i in range(len(rounds) - 1):
            round_events = rounds[i]
            rewards = extract_rewards(round_events)
            response = extract_attempts(round_events)[0]["response"]
            reveal = extract_reveals(round_events)[0]["values"]["x1"]

            builder.start_section(f"round{i}")
            if response == reveal:
                builder.add_line(f"<prefix>{response}</prefix>")
            else:
                builder.add_line(f"<move>{response}</move>")
                builder.add_line(f"<prefix>{reveal}</prefix>")

            # Format the score
            builder.start_section("score")
            builder.add_lines(format_reward(rewards[0])[0])
            builder.end_section()

            builder.end_section()

        # Current round marker
        builder.add_current_round_marker(round_number)
        builder.end_section()

        builder.add_line("")
        if best_score is not None:
            builder.add_line(f"Best score achieved: {best_score:.3f}")

        builder.add_line("Remember: You want to maximize your score. Higher is better!")
        builder.add_line("")

    builder.add_line("Provide your prefix in <move></move> tags.")

    return builder.render()
