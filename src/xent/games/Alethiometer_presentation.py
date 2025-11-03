from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    format_reward,
    split_rounds,
)


def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    history = full_history if full_history is not None else since_events
    b = ChatBuilder()

    # One-time introduction with target story and valid symbols
    if not ctx.get("intro_sent", False):
        story = state.get("s", "")
        valid_symbols = state.get("s1", "")

        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s=story())
assign(s1="alpha-omega anchor angel ant apple baby beehive bird bread bull camel candle cauldron chameleon compass cornucopia crocodile dolphin elephant globe griffin helmet horse hourglass lute madonna marionette moon owl serpent sun sword thunderbolt tree walled-garden wild-man")
elicit(x, 40)
ensure(only_uses_words(s1, x))
assign(x1="Lyra bent over her Alethiometer. The dial spun to these symbols: \"" + x + "\". Lyra looked up and said \"it tells me this\":")
reward(xed(s | x1))
</gameCode>

In this game, you are given a target story and a set of mystical symbols. Your goal is to select and arrange symbols that, when read through Lyra's Alethiometer, best predict the given story.

Think of this as reverse prompt engineering: you know the output (the story) and must craft the optimal input (symbol sequence) to make that output most likely.

Your symbols will be inserted into this template:
"Lyra bent over her Alethiometer. The dial spun to these symbols: \"[YOUR_SYMBOLS]\". Lyra looked up and said \"it tells me this\":"

The game then measures how predictable the story becomes after this prompt. The scoring formula is:
Score = crossEntropy(story) - crossEntropy(story | prompt_with_your_symbols)

A higher score means your symbols create a better prompt that makes the story more predictable. The baseline is just the story without any prompt context.

Your goal is to maximize your score by finding the symbol combination that best connects to the story's themes, characters, or events. Each symbol can carry multiple meanings - like the actual Alethiometer from His Dark Materials.

You have multiple rounds to optimize your score. After each attempt, you'll see:
- Your total score (higher is better)
- Per-token cross-entropy showing which parts of the story responded best to your symbols
Use this feedback to refine your symbol choices in subsequent rounds. Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.


Your symbol sequence can be up to 40 characters long. You MUST use only the valid symbols provided below. Any invalid symbols will cause your attempt to be rejected.

Provide your symbol sequence in <move></move> tags. Any other text in your response will be ignored."""

        builder.add_header(header)
        builder.add_line("")
        builder.add_line(f"<targetStory>{story}</targetStory>")
        builder.add_line("")
        builder.add_line("<validSymbols>")
        builder.add_line(str(valid_symbols))
        builder.add_line("</validSymbols>")
        builder.add_line("")
        builder.add_line("Provide your symbol sequence in <move></move> tags.")

        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # Subsequent turns: either show reward or failed ensure, then prompt
    builder = PresentationBuilder()

    # Check for reward since last elicit
    recent_rewards = [e for e in since_events if e.get("type") == "reward"]
    if recent_rewards:
        # Show last reward summary
        reward_event = recent_rewards[-1]
        builder.start_section("score")
        builder.add_lines(format_reward(reward_event)[0])
        builder.end_section()
        builder.add_line("")

        # Best score so far (across history)
        rounds = split_rounds(history)
        all_rewards = []
        for r in rounds:
            all_rewards.extend([e for e in r if e.get("type") == "reward"])
        if all_rewards:
            best = None
            for r in all_rewards:
                _s, val = format_reward(r)
                if best is None or val > best:
                    best = val
            if best is not None:
                builder.add_line(f"Best score achieved: {best}")
                builder.add_line("")

        builder.add_line(
            "Remember: Use only the valid symbols shown above. Each symbol can appear multiple times."
        )
        builder.add_line("")
        builder.add_line("Provide your symbol sequence in <move></move> tags.")
        b.user(builder.render())
        return b.render(), ctx

    # Otherwise, assume failed ensure since the previous move
    builder.add_line("Contains invalid symbols not in the allowed set.")
    builder.add_line("Provide your symbol sequence in <move></move> tags.")
    b.user(builder.render())
    return b.render(), ctx
