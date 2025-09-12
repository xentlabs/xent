from xega.presentation.sdk import (
    PresentationBuilder,
    extract_attempts,
    extract_rewards,
    format_attempt,
    format_reward,
    split_rounds,
)


def present(state, history, metadata):
    # Extract game state
    story = state["s"]
    valid_symbols = state["s1"]

    # Build presentation
    builder = PresentationBuilder()

    # Rich header with complete game explanation
    header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s=story())
assign(s1="alpha-omega anchor angel ant apple baby beehive bird bread bull camel candle cauldron chameleon compass cornucopia crocodile dolphin elephant globe griffin helmet horse hourglass lute madonna marionette moon owl serpent sun sword thunderbolt tree walled-garden wild-man")
elicit(x, 40)
ensure(only_uses_words(s1, x))
assign(x1="Lyra bent over her Alethiometer. The dial spun to these symbols: \"" + x + "\". Lyra looked up and said \"it tells me this\":")
reward(xed(s | x1))
</gameCode>

In this game, you are given a target story and a set of mystical symbols. Your goal is to select and arrange symbols that, when read through Lyra's Alethiometer, best predict the given story.

Think of this as reverse prompt engineering: you know the output (the story) and must craft the optimal input (symbol sequence) to make that output most likely.

Your symbols will be inserted into this template:
"Lyra bent over her Alethiometer. The dial spun to these symbols: \"[YOUR_SYMBOLS]\". Lyra looked up and said \"it tells me this\":"

The game then measures how predictable the story becomes after this prompt. The scoring formula is:
Score = crossEntropy(story) - crossEntropy(story | prompt_with_your_symbols)

A higher score means your symbols create a better prompt that makes the story more predictable. The baseline is just the story without any prompt context.

Your goal is to maximize your score by finding the symbol combination that best connects to the story's themes, characters, or events. Each symbol can carry multiple meanings - like the actual Alethiometer from His Dark Materials.

You have multiple rounds to optimize your score. After each attempt, you'll see:
- Your total score (higher is better)
- Per-token cross-entropy showing which parts of the story responded best to your symbols
Use this feedback to refine your symbol choices in subsequent rounds. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.


Your symbol sequence can be up to 40 characters long. You MUST use only the valid symbols provided below. Any invalid symbols will cause your attempt to be rejected.

Provide your symbol sequence in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")
    builder.add_line(f"<targetStory>{story}</targetStory>")
    builder.add_line("")
    builder.add_line("<validSymbols>")
    builder.add_line(str(valid_symbols))
    builder.add_line("</validSymbols>")

    # Split history into rounds
    rounds = split_rounds(history)

    # Track best score
    best_score = None

    # Process and display history
    builder.add_line("")
    builder.add_line("A history of your play so far:")
    builder.add_line("")
    builder.start_section("fullHistory")

    # Process each round
    for i in range(len(rounds) - 1):
        # This is a completed round
        round_score = render_complete_round(rounds[i], builder, i + 1)
        if round_score is not None and (best_score is None or round_score > best_score):
            best_score = round_score

    # Handle current round (if it has any attempts)
    current_round = rounds[-1]
    render_current_round(current_round, builder, len(rounds))

    builder.end_section()

    # Show current game status
    builder.add_line("")
    builder.add_line("Current game status:")
    builder.add_line(f"Target story: {story}")

    if best_score is not None:
        builder.add_line(f"Best score achieved: {best_score:.1f}")

    builder.add_line("")
    builder.add_line(
        "Remember: Use only the valid symbols shown above. Each symbol can appear multiple times."
    )
    builder.add_line("")
    builder.add_line("Provide your symbol sequence in <move></move> tags.")

    return builder.render()


def render_complete_round(round_events, builder, round_num):
    """Render a completed round with all attempts and final score"""

    # Extract attempts with failure tracking
    attempts = extract_attempts(
        round_events, reason="Contains invalid symbols not in the allowed set"
    )

    if not attempts:
        return None

    builder.start_section(f"round{round_num}")
    builder.start_section("symbolSelection")

    # Show all attempts
    for attempt in attempts:
        builder.add_line(format_attempt(**attempt))

    builder.end_section()

    # Get and display score
    rewards = extract_rewards(round_events)
    if rewards:
        reward = rewards[0]
        reward_str, reward_score = format_reward(reward)
        builder.start_section("score")
        builder.add_lines(reward_str)
        builder.end_section()

        builder.end_section()
        return reward_score

    builder.end_section()
    return None


def render_current_round(round_events, builder, round_num):
    """Render the current incomplete round"""

    # Extract attempts
    attempts = extract_attempts(
        round_events, reason="Contains invalid symbols not in the allowed set"
    )

    builder.start_section(f"round{round_num}")
    builder.start_section("symbolSelection")

    # Show any failed attempts
    for attempt in attempts:
        if attempt["failed"]:
            builder.add_line(format_attempt(**attempt))

    # Show where we are
    builder.add_line("You are HERE. Provide a valid symbol sequence.")

    builder.end_section()
    builder.end_section()
