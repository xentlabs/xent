def present(state, history):
    # Get the stories from state
    story_a = state["s1"]
    story_c = state["s2"]

    # Parse history to extract rounds and scores
    rounds = []
    round_number = 1

    i = 0
    while i < len(history):
        if history[i]["type"] == "elicit_response":
            round_data = {"number": round_number, "bridge": history[i]["response"]}

            # Look for the 4 reward events (we only care about first 2)
            reward_count = 0
            scores = []
            for j in range(i + 1, min(i + 10, len(history))):
                if history[j]["type"] == "reward":
                    reward_count += 1
                    if reward_count <= 2:  # Only track first 2 scores
                        scores.append(history[j]["value"])
                    if reward_count == 4:  # Found all 4 rewards
                        break

            if len(scores) == 2:
                round_data["score_abc"] = scores[0]  # nex(s2 | s + s1 + t)
                round_data["score_cba"] = scores[1]  # nex(s1 | s + s2 + t)
                rounds.append(round_data)
                round_number += 1

            i = j + 1 if reward_count == 4 else i + 1
        else:
            i += 1

    # Build the presentation
    output_lines = []

    header = """You are playing a game. In this game you are given 2 short texts A and C. Your goal is to create a bridge text B such that the text ABC makes sense and CBA also makes sense.

The scoring will be computed using the cross entropy of C given AB plus the cross entropy of A given CB. Specifically `-1 * (crossEntropy(C | AB) + crossEntropy(A | CB))`. So the more likely you can make the text in both directions, the higher your score will be.

Your goal is to optimize your score. So try to provide bridge text B (max 10 tokens) such that A→B→C flows naturally and C→B→A also flows naturally.

You will have multiple attempts to improve your score. After each attempt, you will be given the per-token cross entropy of the scored text. Use this information to improve your score on the next round.

Your move can only be 10 tokens long in total. Anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored.
"""
    output_lines.append(header)
    output_lines.append("")
    output_lines.append(f"<storyA>{story_a}</storyA>")
    output_lines.append(f"<storyC>{story_c}</storyC>")
    output_lines.append("")
    output_lines.append("--- Play History ---")
    output_lines.append("")

    # Dynamic history section
    if not rounds:
        output_lines.append(f"Round {round_number} starting.")
    else:
        output_lines.append("<gameHistory>")

        best_total = float("inf")
        for round_data in rounds:
            output_lines.append(f"  <round{round_data['number']}>")
            output_lines.append(f"    <bridge>{round_data['bridge']}</bridge>")

            # Score ABC with per-token breakdown
            score_abc = round_data["score_abc"]
            total_abc = round(score_abc.total_xent(), 3)
            output_lines.append("    <scoreABC>")
            output_lines.append(f"      Total: {total_abc}")
            output_lines.append(f"      Per-token: {str(score_abc)}")
            output_lines.append("    </scoreABC>")

            # Score CBA with per-token breakdown
            score_cba = round_data["score_cba"]
            total_cba = round(score_cba.total_xent(), 3)
            output_lines.append("    <scoreCBA>")
            output_lines.append(f"      Total: {total_cba}")
            output_lines.append(f"      Per-token: {str(score_cba)}")
            output_lines.append("    </scoreCBA>")

            # Combined total
            combined = round(total_abc + total_cba, 3)
            output_lines.append(f"    <combinedTotal>{combined}</combinedTotal>")
            output_lines.append(f"  </round{round_data['number']}>")

            best_total = min(best_total, combined)

        # Current round marker
        output_lines.append(f"  <round{round_number}>")
        output_lines.append("    <current/>")
        output_lines.append(f"  </round{round_number}>")

        output_lines.append("</gameHistory>")
        output_lines.append("")
        output_lines.append(f"Best total: {best_total}")
        output_lines.append("")

    output_lines.append("Provide your bridge text in <move></move> tags.")

    return "\n".join(output_lines)
