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
    if not history:
        output_lines.append("You are starting a new game.")
        output_lines.append(f'The initial text is: "{story}"')
    else:
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
        full_story_so_far = " ".join(successful_texts)

    last_successful_text = state.get("x2")
    if last_successful_text is None:
        last_successful_text = state["s"]

    output_lines.append(f'The full text so far is: "{full_story_so_far}"')
    output_lines.append(
        f'The previous item you are building off of is: "{last_successful_text}"'
    )
    output_lines.append("\nNow provide your next move within the <move></move> tags.")

    return "\n".join(output_lines)
