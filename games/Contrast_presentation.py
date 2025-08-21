def present(state, history):
    s1 = state["s1"]
    s2 = state["s2"]

    # Parse history into rounds
    rounds = []
    current_round_data = {}
    round_number = 1
    best_contrast_score = None

    reward_count = 0
    story_scores = []

    for event in history:
        if event["type"] == "elicit_response":
            current_round_data = {
                "number": round_number,
                "prefix": event["response"],
                "story1_score": None,
                "story2_score": None,
            }
            reward_count = 0
            story_scores = []
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 3)
            story_scores.append({"score": score, "per_token": str(event["value"])})
            reward_count += 1

            # After receiving both rewards, complete the round
            if reward_count == 2:
                current_round_data["story1_score"] = story_scores[0]
                current_round_data["story2_score"] = story_scores[1]
                contrast_score = round(
                    story_scores[0]["score"] + story_scores[1]["score"], 3
                )
                current_round_data["contrast_score"] = contrast_score
                rounds.append(current_round_data)

                if best_contrast_score is None or contrast_score > best_contrast_score:
                    best_contrast_score = contrast_score

                round_number += 1
                current_round_data = {}
                story_scores = []

    # Build the presentation
    output_lines = []

    # Game description header - flowing narrative
    header = """You are playing a contrast game. You will be given two short stories, and your task is to find a prefix that creates maximum contrast between them - a prefix that helps predict the first story while making the second story LESS predictable.

The scoring measures this contrast effect:
- For story 1: Your score measures how much your prefix helps predict it (higher = better)
- For story 2: Your score measures how much your prefix makes it diverge from expectations (higher = better contrast)
- Combined score: `Total Score = [xent(story1) - xent(story1 | prefix)] + [xent(story2 | prefix) - xent(story2)]`

Your goal is to MAXIMIZE this total score. You want a prefix that simultaneously helps predict story 1 while making story 2 surprising - creating maximum contrast between the two stories.

After each attempt, you'll see individual scores showing how well you're helping story 1 and hindering story 2, plus your combined contrast score. You can play multiple rounds to continuously improve your approach.

You cannot use any words that appear in either story (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored.
"""
    output_lines.append(header)
    output_lines.append("")

    # Present the two stories with clear labels
    output_lines.append("The two stories to contrast:")
    output_lines.append(f"<story1>Make this predictable: {s1}</story1>")
    output_lines.append(f"<story2>Make this surprising: {s2}</story2>")

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

            # Story 1 score (predictability boost)
            output_lines.append("      <story1_predictability>")
            output_lines.append(f"        Score: {round_data['story1_score']['score']}")
            output_lines.append(
                f"        Per-token: {round_data['story1_score']['per_token']}"
            )
            output_lines.append("      </story1_predictability>")

            # Story 2 score (surprise factor)
            output_lines.append("      <story2_surprise>")
            output_lines.append(f"        Score: {round_data['story2_score']['score']}")
            output_lines.append(
                f"        Per-token: {round_data['story2_score']['per_token']}"
            )
            output_lines.append("      </story2_surprise>")

            # Combined contrast score
            output_lines.append(
                f"      <contrastScore>{round_data['contrast_score']}</contrastScore>"
            )
            output_lines.append("    </scores>")
            output_lines.append(f"  </round{round_data['number']}>")

        # Current round marker
        output_lines.append(f"  <round{round_number}>")
        output_lines.append("    <current/>")
        output_lines.append(f"  </round{round_number}>")
        output_lines.append("</gameHistory>")
        output_lines.append("")
        output_lines.append(f"Best contrast score achieved: {best_contrast_score}")
        output_lines.append(
            "Remember: MAXIMIZE your score by helping story 1 while hindering story 2!"
        )
        output_lines.append("")

    output_lines.append("Provide your prefix in <move></move> tags.")

    return "\n".join(output_lines)
