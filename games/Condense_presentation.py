from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    extract_reveals,
    extract_rewards,
    format_reward,
    get_max_score,
    split_rounds,
)


def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)
    all_rewards = extract_rewards(history)
    best_score, _ = get_max_score(all_rewards) if all_rewards else (None, None)

    b = ChatBuilder()

    # One-time header and story
    if not ctx.get("intro_sent", False):
        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s=story())
elicit(x, 10)
assign(x1=remove_common_words(x, s))
reveal(x1)
reward(xed(s | x1))
</gameCode>

You will be given a short story, and your task is to provide a prefix that makes that story as predictable as possible. Think of it as providing context that helps predict what comes next.

The scoring measures how much information your prefix provides about the story. Specifically, your score is the difference between the story's baseline cross-entropy and its cross-entropy given your prefix: `Score = crossEntropy(story) - crossEntropy(story | prefix)`. Your goal is to maximize this score. So you want to find a prefix that will most help an LLM predict the story.

After each attempt, you'll see your score and a per-token breakdown of the cross entropy difference. The game automatically restarts after each successful attempt, allowing you to continuously optimize your approach. Use the feedback from previous rounds to improve your score.  Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.

You cannot use any words that appear in the story itself (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

        builder.add_header(header)
        builder.add_line("")
        builder.add_line("The story:")
        builder.start_section("story")
        builder.add_line(str(state.get("s", "")))
        builder.end_section()
        if len(rounds) == 1:
            builder.add_line("First round starting.")
            builder.add_line("")
        builder.add_line("Provide your prefix in <move></move> tags.")
        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # Subsequent turns: summarize last completed round and prompt
    builder = PresentationBuilder()

    # Find the most recent completed round (with a reward)
    last_completed_index = None
    for i in range(len(rounds) - 1, -1, -1):
        if extract_rewards(rounds[i]):
            last_completed_index = i
            break

    if last_completed_index is not None:
        round_events = rounds[last_completed_index]
        rewards = extract_rewards(round_events)

        builder.add_line(f"Round {last_completed_index}:")

        # Show only the normalized prefix revealed
        reveals = extract_reveals(round_events)
        if reveals:
            prefix = reveals[0]["values"].get("x1")
            if prefix is not None:
                builder.add_line(f"<prefix>{prefix}</prefix>")

        # Score
        if rewards:
            builder.start_section("score")
            builder.add_lines(format_reward(rewards[0])[0])
            builder.end_section()

        builder.add_line("")

    if best_score is not None:
        builder.add_line(f"Best score achieved: {best_score:.3f}")

    builder.add_line("")
    builder.add_line("Remember: You want to maximize your score. Higher is better!")
    builder.add_line("")
    builder.add_line("Provide your prefix in <move></move> tags.")

    b.user(builder.render())
    return b.render(), ctx
