def present(state, history):
    story = state["s"]
    valid_symbols = state["s1"]

    # Parse history to extract rounds, attempts, and scores
    rounds = []
    current_round_attempts = []
    round_number = 1

    for i, event in enumerate(history):
        if event["type"] == "elicit_response":
            # Check if next event is a failed ensure (invalid symbols)
            is_failure = (i + 1) < len(history) and history[i + 1][
                "type"
            ] == "failed_ensure"

            if is_failure:
                current_round_attempts.append(event["response"])
            else:
                # Success - record the round
                round_data = {
                    "number": round_number,
                    "failed_attempts": current_round_attempts.copy(),
                    "success": event["response"],
                }

                # Look for the reward event to get score
                for j in range(i + 1, min(i + 5, len(history))):
                    if history[j]["type"] == "reward":
                        round_data["score"] = history[j]["value"]
                        break

                rounds.append(round_data)
                current_round_attempts = []
                round_number += 1

    # Build the presentation
    output_lines = []

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

Provide your symbol sequence in <move></move> tags. Any other text in your response will be ignored.
"""

    output_lines.append(header)
    output_lines.append("")
    output_lines.append(f"<targetStory>{story}</targetStory>")
    output_lines.append("")
    output_lines.append("<validSymbols>")
    output_lines.append(str(valid_symbols))
    output_lines.append("</validSymbols>")
    output_lines.append("")
    output_lines.append("--- Play History ---")
    output_lines.append("")

    # Dynamic history section
    if not rounds and not current_round_attempts:
        # First round, no history yet
        output_lines.append(f"Round {round_number} starting.")
    else:
        # Show game history
        output_lines.append("<gameHistory>")

        best_score = float("-inf")
        # Show completed rounds with detailed scoring
        for round_data in rounds:
            output_lines.append(f"  <round{round_data['number']}>")

            # Show failed attempts if any
            for attempt in round_data["failed_attempts"]:
                output_lines.append(f"    <invalidAttempt>{attempt}</invalidAttempt>")

            # Show successful attempt
            output_lines.append(f"    <symbols>{round_data['success']}</symbols>")

            # Show score with per-token breakdown
            if "score" in round_data:
                score_val = round_data["score"]
                # Try to get total score
                total = score_val.total_xent()

                output_lines.append("    <score>")
                output_lines.append(f"      Total: {total:.3f}")
                output_lines.append(
                    f"      Per-token: {format_token_xent_list(score_val)}"
                )
                output_lines.append("    </score>")

                best_score = max(best_score, total)

            output_lines.append(f"  </round{round_data['number']}>")

        # Show current round if there are attempts or we're past round 1
        if current_round_attempts or rounds:
            output_lines.append(f"  <round{round_number}>")
            for attempt in current_round_attempts:
                output_lines.append(f"    <invalidAttempt>{attempt}</invalidAttempt>")
            output_lines.append("    <current/>")
            output_lines.append(f"  </round{round_number}>")

        output_lines.append("</gameHistory>")
        output_lines.append("")

        if best_score > float("-inf"):
            output_lines.append(f"Best score so far: {best_score:.3f}")
            output_lines.append("")

    output_lines.append("Provide your symbol sequence in <move></move> tags.")

    return "\n".join(output_lines)
