def present(state, history):
    s1 = state["s1"]
    s2 = state["s2"]
    s3 = state["s3"]

    # Parse history into rounds
    rounds = []
    current_round_data = {}
    round_number = 1
    best_total_score = None

    reward_count = 0
    story_scores = []

    for event in history:
        if event["type"] == "elicit_response":
            current_round_data = {
                "number": round_number,
                "prefix": event["response"],
                "story_scores": [],
            }
            reward_count = 0
            story_scores = []
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 3)
            story_scores.append({"score": score, "per_token": str(event["value"])})
            reward_count += 1

            # After receiving all 3 rewards, complete the round
            if reward_count == 3:
                current_round_data["story_scores"] = story_scores
                total_score = round(sum(s["score"] for s in story_scores), 3)
                current_round_data["total_score"] = total_score
                rounds.append(current_round_data)

                if best_total_score is None or total_score > best_total_score:
                    best_total_score = total_score

                round_number += 1
                current_round_data = {}
                story_scores = []

    # Build the presentation
    output_lines = []

    # Game description header - flowing narrative
    header = """You are playing a multi-text synthesis game. You will be given three short stories, and your task is to find a single prefix that works well for ALL three stories - a prefix that helps predict each of them.

The scoring measures how much information your prefix provides about each story. For each story, your score is the difference between its baseline cross-entropy and its cross-entropy given your prefix. Your total score is the sum across all three stories: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2) - xent(story2 | prefix)] + [xent(story3) - xent(story3 | prefix)]`.

Your goal is to MAXIMIZE this total score. You want to find a prefix that simultaneously helps an LLM predict all three stories - a synthesis that captures what they have in common.

After each attempt, you'll see individual scores for each story and your total score. You can play multiple rounds to continuously improve your approach.

You cannot use any words that appear in any of the three stories (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored.
"""
    output_lines.append(header)
    output_lines.append("")

    # Present the three stories
    output_lines.append("The three stories to synthesize:")
    output_lines.append(f"<story1>{s1}</story1>")
    output_lines.append(f"<story2>{s2}</story2>")
    output_lines.append(f"<story3>{s3}</story3>")

    # Game history
    if not rounds:
        output_lines.append("")
        output_lines.append(f"Round {round_number} starting.")
    else:
        output_lines.append("")
        output_lines.append("--- Play History ---")
        output_lines.append("")
        output_lines.append("<gameHistory>")

        for round_data in rounds:
            output_lines.append(f"  <round{round_data['number']}>")
            output_lines.append(f"    <prefix>{round_data['prefix']}</prefix>")
            output_lines.append("    <scores>")

            # Individual story scores
            for i, story_score in enumerate(round_data["story_scores"], 1):
                output_lines.append(f"      <story{i}>")
                output_lines.append(f"        Total: {story_score['score']}")
                output_lines.append(f"        Per-token: {story_score['per_token']}")
                output_lines.append(f"      </story{i}>")

            # Total combined score
            output_lines.append(
                f"      <totalScore>{round_data['total_score']}</totalScore>"
            )
            output_lines.append("    </scores>")
            output_lines.append(f"  </round{round_data['number']}>")

        # Current round marker
        output_lines.append(f"  <round{round_number}>")
        output_lines.append("    <current/>")
        output_lines.append(f"  </round{round_number}>")
        output_lines.append("</gameHistory>")
        output_lines.append("")
        output_lines.append(f"Best total score achieved: {best_total_score}")
        output_lines.append(
            "Remember: You want to MAXIMIZE your total score across all three stories!"
        )
        output_lines.append("")

    output_lines.append("Provide your prefix in <move></move> tags.")

    return "\n".join(output_lines)
