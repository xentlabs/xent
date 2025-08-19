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

### 1. The Game Rules Block

**Always** start with a complete `<gameRules>` block that contains:

```xml
<gameRules>
- Complete explanation of the game objective
- EXPLICIT OPTIMIZATION GOAL (e.g., "Your goal is to maximize/minimize your score")
- Exact scoring formula in mathematical terms
- All constraints and validation rules  
- Token limits and truncation behavior
- Any baseline comparisons or thresholds
- How the optimization works across rounds/attempts
</gameRules>
```

Example from `double_edge` (note the explicit optimization goal):
```python
header = """You are playing a game. In this game you are given 2 short texts A and C. Your goal is to create a bridge text B such that the text ABC makes sense and CBA also makes sense.

The scoring will be computed using the cross entropy of C given AB plus the cross entropy of A given CB. Specifically `-1 * (crossEntropy(C | AB) + crossEntropy(A | CB))`. So the more likely you can make the text in both directions, the higher your score will be.

Your goal is to optimize your score. So try to provide bridge text B (max 10 tokens) such that A→B→C flows naturally and C→B→A also flows naturally.

You will have multiple attempts to improve your score. After each attempt, you will be given the per-token cross entropy of the scored text. Use this information to improve your score on the next round.
"""
```

**Critical**: Always explicitly state the optimization direction:
- "Your goal is to **maximize** your score"
- "Your goal is to **minimize** the cross-entropy"
- "Try to achieve the **highest possible** score across rounds"

### 2. Score Presentation

Present scores in the form most useful for optimization:

```python
# Show total scores
output_lines.append(f"Total: {total_score}")

# Show per-token breakdown when available
# TokenXentList objects can be converted to strings showing per-token values
output_lines.append(f"Per-token: {str(score_object)}")
```

**Important**: The per-token breakdown is NOT for debugging - it's critical optimization information that helps players identify which tokens to adjust.

### 3. History Tracking

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

### 4. State Utilization

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

- [ ] **Front-load all game information** in a structured `<gameRules>` block
- [ ] **Explicitly state the optimization goal** (maximize/minimize score)
- [ ] **Translate internal mechanics** into player-facing rules
- [ ] **Show mathematical formulas** for scoring (in terms players can act on)
- [ ] **Handle multiple rounds** - all games restart after completion
- [ ] **Track game progress** appropriately (rounds and/or steps within rounds)
- [ ] **Present scores** with per-token breakdowns when available
- [ ] **Use structured XML tags** for history and state
- [ ] **Include token limits** and truncation warnings
- [ ] **End with clear move instructions** using `<move></move>` tags
- [ ] **Never expose** internal variable names or implementation details
- [ ] **Minimize redundancy** - static info appears once at the top
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

## Testing Your Presentation

Ask yourself:
1. Could a player understand the complete game from ONLY this presentation?
2. Are all scoring formulas explicit and mathematical?
3. Is the history structure appropriate for the game type?
4. Are per-token scores shown when available?
5. Is everything translated into player-facing terms?
6. Does it end with `<move></move>` instructions?

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