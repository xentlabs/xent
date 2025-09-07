from xega.presentation.sdk import (
    PresentationBuilder,
    format_token_xent_list,
)


def present(state, history):
    # Extract game state
    story = state["s"]
    valid_symbols = state["s1"]

    # Track best score and current round info
    best_score = None
    completed_rounds = 0
    current_round_attempts = []

    # Build presentation
    builder = PresentationBuilder()

    # Rich header with complete game explanation
    header = """You are playing the Alethiometer game. In this game, you are given a target story and a set of mystical symbols (emojis). Your goal is to select and arrange symbols that, when read through Lyra's Alethiometer, best predict the given story.

Think of this as reverse prompt engineering: you know the output (the story) and must craft the optimal input (symbol sequence) to make that output most likely.

Your symbols will be inserted into this template:
"Lyra bent over her Alethiometer. The dial spun to these symbols: \"[YOUR_SYMBOLS]\". Lyra looked up and said \"it tells me this:"

The game then measures how predictable the story becomes after this prompt. The scoring formula is:
Score = crossEntropy(story) - crossEntropy(story | prompt_with_your_symbols)

A HIGHER score means your symbols create a better prompt that makes the story more predictable. The baseline is just the story without any prompt context.

Your goal is to MAXIMIZE your score by finding the symbol combination that best connects to the story's themes, characters, or events. Each symbol can carry multiple meanings - like the actual Alethiometer from His Dark Materials.

You have multiple rounds to optimize your score. After each attempt, you'll see:
- Your total score (higher is better)
- Per-token cross-entropy showing which parts of the story responded best to your symbols
Use this feedback to refine your symbol choices in subsequent rounds.

Your symbol sequence can be up to 40 characters long. You MUST use only the valid symbols provided below. Any invalid symbols will cause your attempt to be rejected.

Provide your symbol sequence in <move></move> tags. Any other text in your response will be ignored."""

    builder.add_header(header)
    builder.add_line("")
    builder.add_line(f"<targetStory>{story}</targetStory>")
    builder.add_line("")
    builder.add_line("<validSymbols>")
    builder.add_line(str(valid_symbols))
    builder.add_line("</validSymbols>")
    builder.add_line("")
    builder.add_line("--- Play History ---")
    builder.add_line("")

    # Process history in single pass, building output as we go
    if not history:
        builder.add_line("Round 1 starting.")
    else:
        builder.start_section("gameHistory")

        # Process history events and render immediately
        round_number = 1
        temp_failed_attempts = []

        for i, event in enumerate(history):
            if event["type"] == "elicit_response":
                # Check if this attempt failed
                is_failure = (i + 1) < len(history) and history[i + 1][
                    "type"
                ] == "failed_ensure"

                if is_failure:
                    # Add to failed attempts for current round
                    temp_failed_attempts.append(event["response"])
                else:
                    # Success - this completes a round
                    completed_rounds += 1

                    # Start rendering this round
                    builder.start_section(f"round{round_number}")

                    # Show failed attempts if any
                    for attempt in temp_failed_attempts:
                        builder.add_line(f"<invalidAttempt>{attempt}</invalidAttempt>")

                    # Show successful attempt
                    builder.add_line(f"<symbols>{event['response']}</symbols>")

                    # Look for the reward event to get score
                    for j in range(i + 1, min(i + 5, len(history))):
                        if history[j]["type"] == "reward":
                            score_val = history[j]["value"]
                            total = score_val.total_xent()

                            # Track best score
                            if best_score is None or total > best_score:
                                best_score = total

                            # Show score with per-token breakdown
                            builder.start_section("score")
                            builder.add_line(f"Total: {total:.3f}")
                            builder.add_line(
                                f"Per-token: {format_token_xent_list(score_val)}"
                            )
                            builder.end_section()
                            break

                    builder.end_section()

                    # Reset for next round
                    temp_failed_attempts = []
                    round_number += 1

        # Track any pending failed attempts for current incomplete round
        current_round_attempts = temp_failed_attempts

        # Show current round if there are attempts or we're past round 1
        if current_round_attempts or completed_rounds > 0:
            builder.start_section(f"round{completed_rounds + 1}")
            for attempt in current_round_attempts:
                builder.add_line(f"<invalidAttempt>{attempt}</invalidAttempt>")
            builder.add_line("<current/>")
            builder.end_section()

        builder.end_section()
        builder.add_line("")

        if best_score is not None:
            builder.add_line(f"Best score so far: {best_score:.3f}")
            builder.add_line("")

    builder.add_line("Provide your symbol sequence in <move></move> tags.")

    return builder.render()
