def present(state, history):
    story = state["s"]

    # Parse history into rounds
    rounds = []
    current_round_data = {}
    round_number = 1
    best_score = None

    for event in history:
        if event["type"] == "elicit_response":
            current_round_data = {"number": round_number, "prefix": event["response"]}
        elif event["type"] == "reward" and current_round_data:
            score = round(event["value"].total_xent(), 3)
            current_round_data["score"] = score
            current_round_data["per_token"] = str(event["value"])
            rounds.append(current_round_data)

            if best_score is None or score > best_score:
                best_score = score

            round_number += 1
            current_round_data = {}

    # Build the presentation
    output_lines = []

    # Game description header - flowing text like double_edge
    header = """You are playing a text prefix game. You will be given a short story, and your task is to provide a prefix that makes that story as predictable as possible. Think of it as providing context that helps predict what comes next.

The scoring measures how much information your prefix provides about the story. Specifically, your score is the difference between the story's baseline cross-entropy and its cross-entropy given your prefix: `Score = crossEntropy(story) - crossEntropy(story | prefix)`. Your goal is to MAXIMIZE this score. So you want to find a prefix that will most help an LLM predict the story.

After each attempt, you'll see your score and a per-token breakdown of the cross entropy difference. The game automatically restarts after each successful attempt, allowing you to continuously optimize your approach. Use the feedback from previous rounds to improve your score.

You cannot use any words that appear in the story itself (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored.
"""
    output_lines.append(header)
    output_lines.append("")

    # Current story
    output_lines.append(f"The story: <story>{story}</story>")

    # Game history
    if not rounds:
        output_lines.append(f"Round {round_number} starting.")
    else:
        output_lines.append("")
        output_lines.append("--- Play History ---")
        output_lines.append("")
        output_lines.append("<gameHistory>")
        for round_data in rounds:
            output_lines.append(f"  <round{round_data['number']}>")
            output_lines.append(f"    <prefix>{round_data['prefix']}</prefix>")
            output_lines.append("    <score>")
            output_lines.append(f"      Total: {round_data['score']}")
            output_lines.append(f"      Per-token: {round_data['per_token']}")
            output_lines.append("    </score>")
            output_lines.append(f"  </round{round_data['number']}>")

        # Current round marker
        output_lines.append(f"  <round{round_number}>")
        output_lines.append("    <current/>")
        output_lines.append(f"  </round{round_number}>")
        output_lines.append("</gameHistory>")
        output_lines.append("")
        output_lines.append(f"Best score achieved: {best_score}")
        output_lines.append(
            "Remember: You want to MAXIMIZE your score. Higher is better!"
        )
        output_lines.append("")

    output_lines.append("Provide your prefix in <move></move> tags.")

    return "\n".join(output_lines)
