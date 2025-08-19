def present(state, history):
    story = state["s"]

    # --- History parsing ---
    successful_texts = [story]
    failures_by_step = []
    current_step_failures = []

    for i, event in enumerate(history):
        if event["type"] == "elicit_response":
            is_failure = (i + 1) < len(history) and history[i + 1][
                "type"
            ] == "failed_ensure"

            if is_failure:
                current_step_failures.append(event["response"])
            else:
                successful_texts.append(event["response"])
                failures_by_step.append(current_step_failures)
                current_step_failures = []

    # --- Presentation building ---

    output_lines = []
    header = f"""You are playing a game. 

<gameRules>
You will be given a start text. You are going to construct a sequence of 10 short texts which follow that start text. Each of the texts must make sense and be likely to come after the previous text. Your score will be how unlikely the last text is given the first.

So the idea is to make a series of texts which, in sequence, are likely and predictable. But the first and last text are extremely unlikely.

The likelyhood is judged by an LLM. If we are looking at the likelyhook of a text `s` given a text `t`, we will compute that as -1 * cross-entropy(s | t). So the more that `t` helps predict `s`, the higher the score.


The score is judged in the same way. So if you have a start text `s` and a final text `x`, then your score will be cross-entropy(x | s). The more unlikely x is given s, the higher your score.

To determine whether each text is predictable in sequence, we will use a baseline comparison of cross-entropy(" comes the sun" | "After the rain"). So if you have `x1` and `x2` as two texts in your sequence, then those are valid if cross-entropy(x1 | x2) < cross-entropy(" comes the sun" | "After the rain").

Each text you provide can be at most 5 tokens long, anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored.
</gameRules>

Here is the start text for this game:
<startText>
{story}
</startText>

<objectiveReminder>
Remember, you are trying to construct a series of texts that each connect to the previous such that it meets the critera of being more likely than " comes the sun" given "After the rain". The goal is to make the final text as unlikely as possible given the first text.
</objectiveReminder>
"""
    output_lines.append(header)

    # --- History display ---)
    if len(successful_texts) > 1 or len(current_step_failures) > 0:
        output_lines.append("A history of your play so far:")
        output_lines.append("\n<fullHistory>")

        # Completed steps
        for i, failures in enumerate(failures_by_step):
            prompt_text = successful_texts[i]
            success_text = successful_texts[i + 1]
            output_lines.append(f'  <step index="{i + 1}">')
            output_lines.append(
                f'    <prompt>Continuing from: "{prompt_text}"</prompt>'
            )
            if failures:
                output_lines.append("    <failures>")
                for attempt in failures:
                    output_lines.append(f'      <attempt>"{attempt}"</attempt>')
                output_lines.append("    </failures>")
            output_lines.append(f'    <success>"{success_text}"</success>')
            output_lines.append("  </step>")

        # Current, uncompleted step
        if current_step_failures:
            prompt_text = successful_texts[-1]
            output_lines.append(f'  <currentStep index="{len(successful_texts)}">')
            output_lines.append(
                f'    <prompt>Continuing from: "{prompt_text}"</prompt>'
            )
            output_lines.append("    <failures>")
            for attempt in current_step_failures:
                output_lines.append(f'      <attempt>"{attempt}"</attempt>')
            output_lines.append("    </failures>")
            output_lines.append("  </currentStep>")

        output_lines.append("</fullHistory>")

    # --- Summary and Instructions ---

    output_lines.append("\n---")

    full_story_so_far = state.get("s1")
    if full_story_so_far is None:
        full_story_so_far = "".join(successful_texts)

    last_successful_text = state.get("x2")
    if last_successful_text is None:
        last_successful_text = state["s"]

    output_lines.append(f'The full text so far is: "{full_story_so_far}"')
    output_lines.append(
        f'The previous item you are building off of is: "{last_successful_text}"'
    )
    output_lines.append("\nNow provide your next move within the <move></move> tags.")

    return "\n".join(output_lines)
