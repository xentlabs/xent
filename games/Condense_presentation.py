def present(state, history):
    story = state["s"]
    game_overview = f"""I am going to give you a short text. Your job is to provide a string that will prefix that text. Your goal is to minimize the cross-entropy of the text given the prefix you provide. You should respond with what will make the text as likely as possible.

    The text is: "{story}"

    Your response will be used as the prefix to that text and you will be scored on how well it helps predict that text. You may not use any words from the text in your response, regardless of case or punctuation. You can only use a maximum of 10 tokens for your prefix."""
    previous_attempts = []

    for event in history:
        if event["type"] == "elicit_response":
            previous_attempts.append("<attempt>")
            previous_attempts.append("You provided: " + event["response"])
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 2)
            previous_attempts.append(f"Total score for that response: {score}")
            previous_attempts.append(
                f"Per token score for that response: {str(event['value'])}"
            )
            previous_attempts.append("</attempt>")

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
