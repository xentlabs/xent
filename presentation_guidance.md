# Creating Xega Game Presentations for LLM Players

## Understanding Xega Games

Xega games are text-based optimization challenges designed for LLM players. Each game:
- **Defines variables and rules** in a `.xega` file using a domain-specific language
- **Elicits responses** from players (typically text generation tasks)
- **Validates responses** against constraints using `ensure` statements
- **Calculates scores** using cross-entropy metrics (xed, dex, nex functions)
- **Repeats automatically** - After completing a game successfully, another round begins for the player to optimize their score

Key concepts:
- **Cross-entropy scoring**: Measures how surprising/predictable text is given context
- **Iterative optimization**: Players get multiple attempts to improve their score
- **Constraint validation**: Failed constraints restart that step, not the whole game

## Core Philosophy

When creating a presentation for a Xega game, you are building the **complete interface** through which an LLM player experiences and optimizes the game. The presentation must be:

1. **Completely Encapsulated**: The player only sees your presentation, never the `.xega` code. Your presentation IS the game from their perspective.
2. **Optimization-Focused**: Every piece of information should help the player make better moves and improve their score. **Always make it explicit that the goal is to optimize/maximize/minimize the score.**
3. **Mathematically Precise**: LLMs excel at optimization when given exact formulas and constraints.
4. **Front-Loaded**: Put ALL game rules, scoring, and constraints upfront in a structured format.

## The Presentation Function

```python
def present(state: dict, history: list[XegaEvent]) -> str:
    # Your implementation here
```

- **`state`**: Current values of all game variables from the `.xega` file
- **`history`**: List of all game events (elicits, responses, rewards, failures)
- **Returns**: A string that becomes the complete game interface for the player

## Critical Principle: Complete Encapsulation

**The presentation must be self-contained.** Players cannot see:
- Variable names from the `.xega` file
- Internal scoring normalizations
- Implementation details
- The actual game code

Instead, you must **translate** game mechanics into player-facing rules. For example:
- `ensure(xed(x1 | x2) >= xed(t2 | t1))` → "Each text must be more predictable than our baseline"
- Internal normalization against baselines → Present only the scores players need to optimize

## Game Structure Patterns

**Important**: ALL Xega games automatically begin a new round after successful completion, allowing players to optimize their scores across multiple rounds. Your presentation must handle this multi-round nature.

### Pattern 1: Simple Repeated Games
Games where each round is independent (e.g., `double_edge`).

```python
def present(state, history):
    # Parse history into rounds
    rounds = []
    round_number = 1
    
    for i, event in enumerate(history):
        if event["type"] == "elicit_response":
            # Each successful response completes a round
            # Extract scores from reward events
            # Build round data
            rounds.append(round_data)
            round_number += 1
    
    # Build presentation with:
    # 1. Complete game rules upfront with optimization goal
    # 2. History of all completed rounds with scores
    # 3. Best score achieved (and whether to maximize/minimize)
    # 4. Current round indicator
```

### Pattern 2: Multi-Step Games with Rounds
Games with multiple steps per round, where completing all steps ends a round and starts a new one (e.g., `likely_sequence_unlikely_result` has 10 steps per round).

```python
def present(state, history):
    # Track both steps within a round AND multiple rounds
    rounds = []
    current_round_steps = []
    current_step_failures = []
    
    # Parse history to identify:
    # - Completed steps within current round
    # - Completed rounds (when all steps done)
    # - Failed attempts at current step
    
    # Build presentation showing:
    # 1. Complete rules and optimization objective
    # 2. Previous rounds' scores
    # 3. Current round's progress (step X of Y)
    # 4. Current step context and failures
```

## Essential Presentation Components

### 1. The Opening: Narrative Header with Embedded Structure

Start with a flowing narrative that naturally incorporates all game information. This should read smoothly while including precise details:

```python
header = """You are playing a text prefix game. You will be given a short story, and your task is to provide a prefix that makes that story as predictable as possible. Think of it as providing context that helps predict what comes next.

The scoring measures how much information your prefix provides about the story. Specifically, your score is the difference between the story's baseline cross-entropy and its cross-entropy given your prefix: `Score = crossEntropy(story) - crossEntropy(story | prefix)`. Your goal is to MAXIMIZE this score. So you want to find a prefix that will most help an LLM predict the story.

After each attempt, you'll see your score and a per-token breakdown of the cross entropy difference. The game automatically restarts after each successful attempt, allowing you to continuously optimize your approach. Use the feedback from previous rounds to improve your score.

You cannot use any words that appear in the story itself (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored.
"""
```

Key principles:
- **Natural flow**: Reads like a coherent explanation, not a list of rules
- **Embedded precision**: Mathematical formulas and constraints are woven into the narrative
- **Clear optimization goal**: Explicitly states what to maximize/minimize within the context
- **Practical framing**: Explains scoring in terms players can understand ("help an LLM predict")

**Critical**: Always explicitly state the optimization direction:
- "Your goal is to **maximize** your score"
- "Your goal is to **minimize** the cross-entropy"
- "Try to achieve the **highest possible** score across rounds"

### 2. Structured Data Within Natural Flow

After the narrative header, use XML tags for dynamic game data, but present them naturally within the flow:

```python
# Good hybrid approach - natural language introducing structured data
output_lines.append(f"The story: <story>{story}</story>")

# If there's history, introduce it conversationally before the structure
if rounds:
    output_lines.append("")
    output_lines.append("--- Play History ---")
    output_lines.append("")
    output_lines.append("<gameHistory>")
    # ... structured history data ...
    output_lines.append("</gameHistory>")
    output_lines.append("")
    output_lines.append(f"Best score achieved: {best_score}")
    output_lines.append("Remember: You want to MAXIMIZE your score. Higher is better!")
```

This combines:
- **Readable transitions**: "--- Play History ---" introduces the structured section
- **Clean data structure**: XML tags for parseable history
- **Natural reminders**: Optimization hints in plain language after the data

### 3. Score Presentation: Clarity Through Hierarchy

Present scores with both structure and explanation:

```python
# Within structured history
output_lines.append("    <score>")
output_lines.append(f"      Total: {round_data['score']}")
output_lines.append(f"      Per-token: {round_data['per_token']}")
output_lines.append("    </score>")

# Followed by natural language interpretation
output_lines.append(f"Best score achieved: {best_score}")
output_lines.append("Remember: You want to MAXIMIZE your score. Higher is better!")
```

The structured data provides precision while the natural language provides interpretation.

**Important**: The per-token breakdown is NOT for debugging - it's critical optimization information that helps players identify which tokens to adjust.

### 4. History Tracking

Use structured XML-style tags for clear parsing:

```xml
<gameHistory>
  <round1>
    <move>player's attempt</move>
    <scoreBreakdown>
      Total: -5.23
      Per-token: [tok1: -0.5, tok2: -1.2, ...]
    </scoreBreakdown>
  </round1>
  <round2>
    <current/>
  </round2>
</gameHistory>
```

### 5. State Utilization

Use state variables to provide context:

```python
# Access state variables
current_context = state.get("x2", state["s"])
full_sequence = state.get("s1", "")

# Present them in player-facing terms
output_lines.append(f'Previous text: "{current_context}"')
output_lines.append(f'Full sequence so far: "{full_sequence}"')
```

## Implementation Checklist

When implementing a presentation function:

- [ ] **Start with a narrative header** that naturally explains the game
- [ ] **Embed mathematical formulas** within the flowing explanation using backticks
- [ ] **State optimization goal explicitly** within the narrative context
- [ ] **Use structured XML for dynamic data** (history, scores, current state)
- [ ] **Introduce structured sections naturally** with headers like "--- Play History ---"
- [ ] **Follow structure with interpretation** (e.g., "Best score: X" after history)
- [ ] **Handle multiple rounds** - all games restart after completion
- [ ] **Track game progress** appropriately (rounds and/or steps within rounds)
- [ ] **Present scores** with per-token breakdowns when available
- [ ] **Include token limits** and truncation warnings
- [ ] **End with clear move instructions** using `<move></move>` tags
- [ ] **Never expose** internal variable names or implementation details
- [ ] **Avoid redundancy** - static info in header, dynamic info in structured sections
- [ ] **Show best score** and remind players they're optimizing across rounds

## Common Anti-Patterns to Avoid

### ❌ Exposing Internal Variables
```python
# BAD: Exposes internal variable names
output_lines.append(f"Variable x1 = {state['x1']}")

# GOOD: Translates to player-facing concept
output_lines.append(f"Your current text: {state['x1']}")
```

### ❌ Hiding Scoring Details
```python
# BAD: Vague scoring explanation
output_lines.append("Try to maximize your score")

# GOOD: Precise mathematical formula
output_lines.append("Score = -1 * crossEntropy(finalText | initialText)")
```

### ❌ Repeating Static Information
```python
# BAD: Rules repeated every round
for round in rounds:
    output_lines.append("Rules: You must use valid symbols...")

# GOOD: Rules appear once at the top
output_lines.append(header_with_rules)  # Once
# Then only dynamic history below
```

### ❌ Missing Token Breakdowns
```python
# BAD: Only showing total score
output_lines.append(f"Score: {total}")

# GOOD: Including per-token information
output_lines.append(f"Total: {total}")
output_lines.append(f"Per-token: {str(token_scores)}")
```

### ❌ Pure Structure Without Context
```python
# BAD: Only structured data, no narrative
<gameRules>
- Objective: Minimize cross-entropy
- Formula: xed(s | x)
- Constraints: 10 tokens max
</gameRules>

# GOOD: Narrative explanation with embedded details
"""You are playing a text prefix game. Your task is to provide a prefix that makes 
the story as predictable as possible... Specifically: `Score = crossEntropy(story) - 
crossEntropy(story | prefix)`. Your goal is to MAXIMIZE this score..."""
```

### ❌ Pure Narrative Without Structure
```python
# BAD: Everything in prose, hard to parse history
"In round 1 you tried 'Once upon a' and got 5.2. In round 2..."

# GOOD: Narrative intro with structured history
"--- Play History ---"
<gameHistory>
  <round1>...</round1>
</gameHistory>
```

## Example: Analyzing `likely_sequence_unlikely_result_presentation.py`

This exemplary presentation demonstrates several best practices:

1. **Complete upfront specification** - The `<gameRules>` block explains everything including the baseline comparison
2. **No round structure** - Uses steps instead, since it's a sequential puzzle
3. **Context preservation** - Shows "Continuing from: [text]" for each step
4. **Objective reminders** - Includes `<objectiveReminder>` to reinforce the goal
5. **State utilization** - Uses `state["x2"]` and `state["s1"]` to show context

## Example: Analyzing `double_edge_presentation.py`

This presentation excels at:

1. **Score abstraction** - Doesn't show internal normalization, only relevant scores
2. **Bidirectional clarity** - Makes the A→B→C and C→B→A concept crystal clear
3. **Per-token feedback** - Shows `TokenXentList` string representation for optimization
4. **Clean history structure** - Uses consistent XML tags for parsing
5. **Combined scoring** - Shows individual direction scores AND combined total

## Example: The Hybrid Approach in Condense

The Condense presentation exemplifies the hybrid approach:

1. **Narrative opening**: Explains the game naturally with embedded formulas
2. **Structured data**: `<story>`, `<gameHistory>`, `<round>` tags for clarity
3. **Natural transitions**: "--- Play History ---" introduces structured sections  
4. **Contextual reminders**: "Remember: You want to MAXIMIZE your score" after data

This combination ensures both human readability and LLM parseability.

## Testing Your Presentation

Ask yourself:
1. Could a player understand the complete game from ONLY this presentation?
2. Are all scoring formulas explicit and mathematical?
3. Is the history structure appropriate for the game type?
4. Are per-token scores shown when available?
5. Is everything translated into player-facing terms?
6. Does it end with `<move></move>` instructions?
7. Does it combine narrative flow with structured data effectively?

## The XegaEvent Types Reference

For parsing the history, here are the event types you'll encounter:

```python
# Player provides input
ElicitResponseEvent: {"type": "elicit_response", "response": str, ...}

# Validation failed  
FailedEnsureEvent: {"type": "failed_ensure", ...}

# Score received
RewardEvent: {"type": "reward", "value": TokenXentList, ...}

# Values revealed
RevealEvent: {"type": "reveal", "values": dict, ...}
```

The `TokenXentList` in reward events can be converted to a string showing per-token cross-entropy values - this is crucial optimization information for players.

## Final Principle: You Are Building an Optimizer's Interface

Remember: LLM players are optimizers. They need:
- Complete specifications upfront
- Precise mathematical formulas
- Granular feedback (per-token scores)
- Clear structure for parsing
- No narrative fluff or hidden information

Your presentation is their only window into the game. Make it count.