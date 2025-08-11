def present(state, history):
    s1 = state["s1"]
    s2 = state["s2"]
    s3 = state["s3"]
    game_overview = f"""I am going to give you 3 short texts. Your job is to provide a string that will prefix those texts. Your goal is to minimize the cross-entropy of each of the texts given the prefix you provide. You should respond with what will make the text as likely as possible.

First text: "{s1}"
Second text: "{s2}"
Third text: "{s3}"

Your response will be used as a prefix to each of those texts and you will be scored on how well it helps predict those texts. Your score will be the sum of the cross entropy of the texts given the prefix. You may not use any words from any of the texts in your response, regardless of case or punctuation. You can only use a maximum of 10 tokens for your prefix."""
    previous_attempts = []

    reward_count = 0
    for event in history:
        if event["type"] == "elicit_response":
            previous_attempts.append("<attempt>")
            previous_attempts.append("You provided: " + event["response"])
        elif event["type"] == "reward":
            text = (
                "first"
                if reward_count == 0
                else "second"
                if reward_count == 1
                else "third"
            )
            score = round(event["value"].total_xent(), 2)
            previous_attempts.append(f"Total score for the {text} text: {score}")
            previous_attempts.append(
                f"Per token score for the {text} text: {str(event['value'])}"
            )
            reward_count += 1
            if reward_count == 3:
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
