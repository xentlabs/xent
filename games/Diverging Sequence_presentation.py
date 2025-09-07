from xega.presentation.sdk import (
    PresentationBuilder,
)


def present(state, history):
    story = state["s"]

    # Build presentation
    builder = PresentationBuilder()

    # Game header
    header = f"""You are playing a game. 

<gameRules>
You will be given a start text `S`. You are going to construct a sequence of 2 short texts, `t1` which follows `S` and `t2` which follows the concatenation `S+t1`. `t1` must make sense and be likely to come after `S`. `t2` must make sense and be likely to come after `S+t2`. Your score will be how unlikely `t2` is given `S`.

So the idea is to make a series of texts which, in sequence, are likely and predictable. But the first and last text are extremely unlikely.

The likelyhood is judged by an LLM. If we are looking at the likelyhood of a text `t` given a text `s`, we will compute that as -1 * cross-entropy(t | s). So the more that `s` helps predict `t`, the higher the likelyhood.

To determine whether `t1` and `t2` are predictable in sequence, we will use a baseline comparison of cross-entropy(" I eat food" | "After the rain"). So `t1` is valid if -1 * cross-entropy(t1 | S) > -1 * cross-entropy(" I eat food" | "After the rain") and `t2` is valid if -1 * cross-entropy(t2 | S+t1) > -1 * cross-entropy(" I eat food" | "After the rain").

The score is judged in the same way. So if you have a start text `S` and a final text `t2`, then your score will be cross-entropy(t2 | s). The more unlikely `t2` is given `S,` the higher your score - but keep in mind the constraints of likelihood on `t1` and `t2`.

Each text you provide can be at most 5 tokens long, anything beyond that will be truncated. Provide your move in <move></move> tags. Any other text in your response will be ignored.
</gameRules>

Here is the start text for this game:
<startText>
{story}
</startText>

<objectiveReminder>
Remember, you are trying to construct a series of texts that each connect to the previous such that it meets the critera of being more likely than " comes the sun" given "After the rain". The goal is to make the final text as unlikely as possible given the first text.
</objectiveReminder>"""

    builder.add_header(header)

    # Parse history to track successful texts and failures per step
    successful_texts = [story]
    failures_by_step = []
    current_step_failures = []

    # Process history and track successes/failures
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

    # History display
    if len(successful_texts) > 1 or len(current_step_failures) > 0:
        builder.add_line("A history of your play so far:")
        builder.add_line("")
        builder.start_section("fullHistory")

        # Completed steps - render immediately as we process
        for i, failures in enumerate(failures_by_step):
            prompt_text = successful_texts[i]
            success_text = successful_texts[i + 1]
            builder.start_section("step", index=i + 1)
            builder.add_line(f'<prompt>Continuing from: "{prompt_text}"</prompt>')

            if failures:
                builder.start_section("failures")
                for attempt in failures:
                    builder.add_line(f'<attempt>"{attempt}"</attempt>')
                builder.end_section()

            builder.add_line(f'<success>"{success_text}"</success>')
            builder.end_section()

        # Current, uncompleted step
        if current_step_failures:
            prompt_text = successful_texts[-1]
            builder.start_section("currentStep", index=len(successful_texts))
            builder.add_line(f'<prompt>Continuing from: "{prompt_text}"</prompt>')
            builder.start_section("failures")
            for attempt in current_step_failures:
                builder.add_line(f'<attempt>"{attempt}"</attempt>')
            builder.end_section()
            builder.end_section()

        builder.end_section()

    # Summary and Instructions
    builder.add_line("")
    builder.add_line("---")

    full_story_so_far = state.get("s1")
    if full_story_so_far is None:
        full_story_so_far = "".join(successful_texts)

    last_successful_text = state.get("x2")
    if last_successful_text is None:
        last_successful_text = state["s"]

    builder.add_line(f'The full text so far is: "{full_story_so_far}"')
    builder.add_line(
        f'The previous item you are building off of is: "{last_successful_text}"'
    )
    builder.add_line("")
    builder.add_line("Now provide your next move within the <move></move> tags.")

    return builder.render()
