import ast
from typing import List

from xega.common.xega_types import (
    ExpandedGameConfig,
    ExpandedXegaBenchmarkConfig,
    GameConfig,
    XegaBenchmarkConfig,
    XegaGameConfig,
)
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
) -> List[ExpandedGameConfig]:
    game_configs: List[ExpandedGameConfig] = []
    for map_num in range(benchmark_config["num_maps_per_game"]):
        map_seed = f"{map_num}"
        judge.set_seed(benchmark_config["seed"], map_seed)
        expanded_game_config = expand_game_config(game, map_seed, judge)
        game_configs.append(expanded_game_config)

    return game_configs


def expand_game_config(
    game_config: GameConfig, map_seed: str, judge: Judge
) -> ExpandedGameConfig:
    expanded_code = preprocess_dsl_code(game_config["code"], judge)

    return ExpandedGameConfig(
        name=game_config["name"],
        code=expanded_code,
        map_seed=map_seed,
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


def preprocess_dsl_code(code: str, judge: Judge) -> str:
    lines = code.splitlines()
    new_lines: List[str] = []
    for line in lines:
        line = line.strip()
        tree = ast.parse(line)
        rewriter = StoryRewriter(judge)
        new_tree = rewriter.visit(tree)
        ast.fix_missing_locations(new_tree)
        rewritten_code = ast.unparse(new_tree)
        new_lines.append(rewritten_code)
    return "\n".join(new_lines)
