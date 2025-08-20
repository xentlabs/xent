import ast
import io
import tokenize

from xega.common.xega_types import (
    ExpandedGameConfig,
    ExpandedXegaBenchmarkConfig,
    GameConfig,
    XegaBenchmarkConfig,
    XegaGameConfig,
)
from xega.presentation.executor import get_default_presentation
from xega.runtime.judge import Judge


def expand_benchmark_config(
    benchmark_config: XegaBenchmarkConfig,
) -> ExpandedXegaBenchmarkConfig:
    judge = Judge(benchmark_config["judge_model"])
    expanded_benchmark_config = ExpandedXegaBenchmarkConfig(
        config_type="expanded_benchmark_config",
        judge_model=benchmark_config["judge_model"],
        npc_players=benchmark_config["npc_players"],
        num_variables_per_register=benchmark_config["num_variables_per_register"],
        max_steps=benchmark_config["max_steps"],
        auto_replay=benchmark_config["auto_replay"],
        seed=benchmark_config["seed"],
        num_maps_per_game=benchmark_config["num_maps_per_game"],
        games=[],
        benchmark_id=benchmark_config["benchmark_id"],
    )

    for game in benchmark_config["games"]:
        game_configs = build_game_configs_from_benchmark_config(
            game, benchmark_config, judge
        )
        for game_config in game_configs:
            for player_set in benchmark_config["players"]:
                if len(player_set) != 1:
                    raise Exception(
                        "Currently only single player benchmarks are supported"
                    )
                player = player_set[0]
                full_game_config = XegaGameConfig(
                    game=game_config,
                    players=[player],
                    map_seed=game_config["map_seed"],
                    judge_model=benchmark_config["judge_model"],
                    npc_players=benchmark_config["npc_players"],
                    num_variables_per_register=benchmark_config[
                        "num_variables_per_register"
                    ],
                    max_steps=benchmark_config["max_steps"],
                    auto_replay=benchmark_config["auto_replay"],
                    seed=benchmark_config["seed"],
                    num_maps_per_game=benchmark_config["num_maps_per_game"],
                )
                expanded_benchmark_config["games"].append(full_game_config)

    return expanded_benchmark_config


def build_game_configs_from_benchmark_config(
    game: GameConfig,
    benchmark_config: XegaBenchmarkConfig,
    judge: Judge,
) -> list[ExpandedGameConfig]:
    game_configs: list[ExpandedGameConfig] = []
    for map_num in range(benchmark_config["num_maps_per_game"]):
        map_seed = f"game{game['name']}_map{map_num}"
        judge.set_seed(benchmark_config["seed"], map_seed)
        expanded_game_config = expand_game_config(game, map_seed, judge)
        game_configs.append(expanded_game_config)

    return game_configs


def expand_game_config(
    game_config: GameConfig, map_seed: str, judge: Judge
) -> ExpandedGameConfig:
    expanded_code = preprocess_dsl_code(game_config["code"], judge)
    presentation_function = game_config.get("presentation_function")
    if presentation_function is None:
        presentation_function = get_default_presentation()

    return ExpandedGameConfig(
        name=game_config["name"],
        code=expanded_code,
        map_seed=map_seed,
        presentation_function=presentation_function,
    )


class StoryRewriter(ast.NodeTransformer):
    def __init__(self, judge: Judge):
        super().__init__()
        self.judge = judge

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "story":
            new_node = ast.Constant(value=self.judge.generate_text())
            ast.copy_location(new_node, node)
            return new_node
        return node


def extract_comment_and_code(line: str) -> tuple[str, str]:
    """Extract code and comment parts from a line.
    Returns (code_part, comment_part)
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(line).readline))
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comment_start = token.start[1]
                code_part = line[:comment_start].rstrip()
                comment_part = line[comment_start:]
                return code_part, comment_part
    except tokenize.TokenError:
        # If tokenization fails, treat the whole line as code
        pass
    return line, ""


def preprocess_dsl_code(code: str, judge: Judge) -> str:
    lines = code.splitlines()
    new_lines: list[str] = []

    for line in lines:
        stripped_line = line.strip()

        # If it's an empty line, keep it as-is
        if not stripped_line:
            new_lines.append(line)
            continue

        # If it's a full-line comment, keep it as-is
        if stripped_line.startswith("#"):
            new_lines.append(line)
            continue

        # Extract code and comment parts
        code_part, comment_part = extract_comment_and_code(line)

        # If there's no actual code (just whitespace), keep original
        if not code_part.strip():
            new_lines.append(line)
            continue

        # Transform the code part
        try:
            # Get the indentation from the original line
            original_indent = len(line) - len(line.lstrip())

            tree = ast.parse(code_part.strip())
            rewriter = StoryRewriter(judge)
            new_tree = rewriter.visit(tree)
            ast.fix_missing_locations(new_tree)
            rewritten_code = ast.unparse(new_tree)

            # Reconstruct the line with original indentation
            if comment_part:
                new_line = " " * original_indent + rewritten_code + " " + comment_part
            else:
                new_line = " " * original_indent + rewritten_code

            new_lines.append(new_line)
        except SyntaxError:
            # If parsing fails, keep the original line
            new_lines.append(line)

    return "\n".join(new_lines)
