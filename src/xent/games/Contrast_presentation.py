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

You will be given two short stories, and your task is to find a prefix that creates maximum contrast between them - a prefix that helps predict the first story while making the second story less predictable.

The scoring measures this contrast effect:
- For story 1: Your score measures how much your prefix helps predict it (higher = better)
- For story 2: Your score measures how much your prefix makes it diverge from expectations (higher = better contrast)
- Combined score: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2 | prefix) - xent(story2)]`

Your goal is to maximize this total score. You want a prefix that simultaneously helps predict story 1 while making story 2 surprising - creating maximum contrast between the two stories.

After each attempt, you'll see individual scores showing how well you're helping story 1 and hindering story 2, plus your combined contrast score. You can play multiple rounds to continuously improve your approach. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.

You cannot use any words that appear in either story (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

        builder.add_header(header)
        builder.add_line("")
        s1 = state.get("s1", "")
        s2 = state.get("s2", "")
        builder.add_line("The two stories to contrast:")
        builder.add_line(f"Make this predictable: <story1>{s1}</story1>")
        builder.add_line(f"Make this surprising: <story2>{s2}</story2>")
        builder.add_line("")
        builder.add_line("Round 1 starting.")
        builder.add_line("")
        builder.add_line("Provide your prefix in <move></move> tags.")
        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    builder = PresentationBuilder()

    last_completed_index = None
    for i in range(len(rounds) - 1, -1, -1):
        if extract_rewards(rounds[i]):
            last_completed_index = i
            break

    best_contrast_score = None
    for i in range(len(rounds)):
        rewards = extract_rewards(rounds[i])
        if len(rewards) >= 2:
            story1_val = format_reward(rewards[0])[1]
            story2_val = format_reward(rewards[1])[1]
            total = round(story1_val + story2_val, 3)
            if best_contrast_score is None or total > best_contrast_score:
                best_contrast_score = total

    if last_completed_index is not None:
        round_events = rounds[last_completed_index]
        rewards = extract_rewards(round_events)
        builder.add_line(f"Round {last_completed_index}:")
        reveals = extract_reveals(round_events)
        if reveals:
            prefix = reveals[0]["values"].get("x1")
            if prefix is not None:
                builder.add_line(f"<prefix>{prefix}</prefix>")
        if len(rewards) >= 2:
            builder.start_section("scores")
            story1_str, story1_val = format_reward(rewards[0])
            builder.start_section("story1_predictability")
            builder.add_lines(story1_str)
            builder.end_section()
            story2_str, story2_val = format_reward(rewards[1])
            builder.start_section("story2_surprise")
            builder.add_lines(story2_str)
            builder.end_section()
            contrast_score = round(story1_val + story2_val, 3)
            builder.add_line(f"<contrastScore>{contrast_score}</contrastScore>")
            builder.end_section()
        builder.add_line("")

    if best_contrast_score is not None:
        builder.add_line(f"Best contrast score achieved: {best_contrast_score}")
        builder.add_line(
            "Remember: maximize your score by helping story 1 while hindering story 2!"
        )
    builder.add_line("")
    builder.add_line("Provide your prefix in <move></move> tags.")
    b.user(builder.render())
    return b.render(), ctx
