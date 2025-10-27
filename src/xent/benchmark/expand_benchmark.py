import ast
import io
import tokenize

from xent.common.configuration_types import (
    CondensedXentBenchmarkConfig,
    ExpandedXentBenchmarkConfig,
    GameConfig,
    GameMapConfig,
    XentMetadata,
)
from xent.common.errors import XentSyntaxError
from xent.runtime.judge import Judge
from xent.runtime.text_generation.corpus_generation import CommunityArchiveTextGenerator
from xent.runtime.text_generation.text_generation import TextGenerator


def expand_benchmark_config(
    condensed_config: CondensedXentBenchmarkConfig,
) -> ExpandedXentBenchmarkConfig:
    text_generator_config = condensed_config["expansion_config"][
        "text_generation_config"
    ]
    text_generator: TextGenerator | None = None
    if text_generator_config["generator_type"] == "COMMUNITY_ARCHIVE":
        text_generator = CommunityArchiveTextGenerator(
            **text_generator_config["generator_config"]
        )

    judge = Judge(
        condensed_config["metadata"]["judge_model"],
        text_generator=text_generator,
        max_generation_length=text_generator_config["max_length"],
    )
    expanded_benchmark_config = ExpandedXentBenchmarkConfig(
        config_type="expanded_xent_config",
        metadata=XentMetadata(
            judge_model=condensed_config["metadata"]["judge_model"],
            num_rounds_per_game=condensed_config["metadata"]["num_rounds_per_game"],
            seed=condensed_config["metadata"]["seed"],
            benchmark_id=condensed_config["metadata"]["benchmark_id"],
            xent_version=condensed_config["metadata"]["xent_version"],
            store_full_player_interactions=condensed_config["metadata"].get(
                "store_full_player_interactions", False
            ),
            npcs=condensed_config["metadata"].get("npcs", []),
        ),
        players=condensed_config["players"],
        games=condensed_config["games"],
        maps=[],
    )

    for game in condensed_config["games"]:
        game_map_configs = build_game_configs_from_condensed_config(
            game, condensed_config, judge
        )
        expanded_benchmark_config["maps"].extend(game_map_configs)

    return expanded_benchmark_config


def build_game_configs_from_condensed_config(
    game: GameConfig,
    condensed_config: CondensedXentBenchmarkConfig,
    judge: Judge,
) -> list[GameMapConfig]:
    game_map_configs: list[GameMapConfig] = []
    for map_num in range(condensed_config["expansion_config"]["num_maps_per_game"]):
        map_seed = f"game{game['name']}_map{map_num}"
        judge.set_seed(condensed_config["metadata"]["seed"], map_seed)
        game_map_config = expand_game_config(game, map_seed, judge)
        game_map_configs.append(game_map_config)

    return game_map_configs


def expand_game_config(
    game_config: GameConfig, map_seed: str, judge: Judge
) -> GameMapConfig:
    expanded_code = preprocess_dsl_code(game_config["code"], judge)
    presentation_function = game_config["presentation_function"]

    return GameMapConfig(
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
        if isinstance(node.func, ast.Name) and node.func.id == "generate_list":
            # Enforce: exactly two positional args (prompt: str, length: int), no keywords
            if node.keywords:
                raise XentSyntaxError(
                    "generate_list requires positional args only: generate_list('<prompt>', <length>)"
                )
            if len(node.args) != 2:
                raise XentSyntaxError(
                    "generate_list requires exactly two positional arguments: prompt (str), length (int)"
                )

            prompt_arg, length_arg = node.args[0], node.args[1]
            if not (
                isinstance(prompt_arg, ast.Constant)
                and isinstance(prompt_arg.value, str)
            ):
                raise XentSyntaxError(
                    "generate_list first argument must be a string literal prompt"
                )
            if not isinstance(length_arg, ast.Constant) or not isinstance(
                length_arg.value, int | float
            ):
                raise XentSyntaxError(
                    "generate_list second argument must be a numeric literal length"
                )

            prompt_val: str = prompt_arg.value  # type: ignore[assignment]
            length_val: int = int(length_arg.value)  # type: ignore[arg-type]

            generated_items = self.judge.generate_list(prompt_val, length_val)
            new_node = ast.List(
                elts=[ast.Constant(value=item) for item in generated_items],
                ctx=ast.Load(),
            )
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
