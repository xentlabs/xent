def present(state, history):
    s1 = state["s1"]
    s2 = state["s2"]
    game_overview = f"""I am going to give you two short texts. Your job is to provide a string such that when the first story is prefixed with your string, the cross entropy of the text is minimized. But when the second story is prefixed with your string, the cross entropy of the text is maximized. So you want to find a string that helps predict the first story, while also making the second story less likely. Your score will be the negative of the cross entropy of the first text plus the cross entropy of the second text.

First text: {s1}
Second text: {s2}

Your string must not use any words from either text, regardless of case or punctuation. Your string must be at most 10 tokens long.

So think hard about what you can say in 10 tokens that will minimize the cross entropy of the first text, while maximizing the cross entropy of the second text."""
    previous_attempts = []

    reward_count = 0
    for event in history:
        if event["type"] == "elicit_response":
            previous_attempts.append("<attempt>")
            previous_attempts.append("You provided: " + event["response"])
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 2)
            text = "first" if reward_count == 0 else "second"
            previous_attempts.append(f"Score for the {text} text: {score}")
            previous_attempts.append(
                f"Per token score for the {text} text: {str(event['value'])}"
            )
            reward_count += 1
            if reward_count == 2:
                previous_attempts.append("</attempt>")
                reward_count = 0

    if len(previous_attempts) == 0:
        instructions = "Provide your prefix inside of `<move></move>` tags. Any other text in your response will be ignored. You will be given feedback on your prefix and a chance to improve your prefix."
        output = [game_overview, instructions]
    else:
        instructions = "Use your previous attempts above to further optimize your prefix. Provide your prefix inside of `<move></move>` tags. Any other text in your response will be ignored."
        output = (
            [game_overview, "<previousAttempts>"]
            + previous_attempts
            + ["</previousAttempts>", instructions]
        )

    return "\n".join(output)
