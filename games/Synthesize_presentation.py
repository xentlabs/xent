from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    extract_reveals,
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

    # One-time header and three stories
    if not ctx.get("intro_sent", False):
        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

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

        s1 = state.get("s1", "")
        s2 = state.get("s2", "")
        s3 = state.get("s3", "")

        builder.add_line("The three stories to synthesize:")
        builder.add_line(f"<story1>{s1}</story1>")
        builder.add_line(f"<story2>{s2}</story2>")
        builder.add_line(f"<story3>{s3}</story3>")
        builder.add_line("")
        builder.add_line("Provide your prefix in <move></move> tags.")

        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # Subsequent turns: summarize last completed round and prompt for the next
    builder = PresentationBuilder()

    # Find the most recent completed round (with rewards)
    last_completed_index = None
    for i in range(len(rounds) - 1, -1, -1):
        if extract_rewards(rounds[i]):
            last_completed_index = i
            break

    best_total = None
    # Compute best total so far across all completed rounds
    for i in range(len(rounds)):
        rewards = extract_rewards(rounds[i])
        if rewards:
            total = 0
            for r in rewards:
                _text, score_val = format_reward(r)
                total += score_val
            if best_total is None or total > best_total:
                best_total = total

    if last_completed_index is not None:
        round_events = rounds[last_completed_index]
        rewards = extract_rewards(round_events)

        builder.add_line(f"Round {last_completed_index}:")

        # Show normalized prefix (omit the move as it's already in chat)
        reveals = extract_reveals(round_events)
        if reveals:
            prefix = reveals[0]["values"].get("x1")
            if prefix is not None:
                builder.add_line(f"<prefix>{prefix}</prefix>")

        # Scores per story and total
        if rewards:
            builder.start_section("scores")
            total_reward = 0
            for story_num, reward in enumerate(rewards):
                builder.start_section(f"story{story_num + 1}")
                reward_str, reward_score = format_reward(reward)
                total_reward += reward_score
                builder.add_lines(reward_str)
                builder.end_section()
            builder.add_line(f"<totalScore>{total_reward}</totalScore>")
            builder.end_section()

        builder.add_line("")

    if best_total is not None:
        builder.add_line(f"Best total score achieved: {best_total}")
        builder.add_line(
            "Remember: You want to maximize your total score across all three stories!"
        )
        builder.add_line("")

    builder.add_line("Provide your prefix in <move></move> tags.")

    b.user(builder.render())
    return b.render(), ctx
