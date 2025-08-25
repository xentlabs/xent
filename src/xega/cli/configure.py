import json
import os
from copy import deepcopy

import click

from xega.benchmark.expand_benchmark import expand_benchmark_config
from xega.cli.cli_util import generate_benchmark_id
from xega.common.util import dumps
from xega.common.xega_types import (
    ExpandedXegaBenchmarkConfig,
    GameConfig,
    PlayerConfig,
    XegaBenchmarkConfig,
    XegaGameConfig,
    XegaMetadata,
)
from xega.presentation.executor import get_single_presentation
from xega.runtime.llm_api_client import guess_provider_from_model

SIMPLE_GAME_CODE = """
assign(s=story())
reveal(black, s)
elicit(black, x, 10)
assign(x1=remove_common_words(x, s)) # Remove any words in story from input text
reward(black, xed(s | x1))
""".strip()


DEFAULT_XEGA_CONFIG = XegaMetadata(
    judge_model="gpt2",
    num_rounds_per_game=30,
    seed="notrandom",
    num_variables_per_register=4,
    npc_players=[],
    num_maps_per_game=1,
)


def games_from_dir(game_dir: str) -> list[GameConfig]:
    files = os.listdir(game_dir)
    game_configs = []
    for file_name in files:
        if not file_name.endswith(".xega"):
            continue
        game_name = file_name[:-5]

        game_path = os.path.join(game_dir, file_name)
        with open(game_path) as f:
            game_code = f.read()

        presentation_function = None
        presentation_path = os.path.join(game_dir, f"{game_name}_presentation.py")
        if os.path.exists(presentation_path):
            with open(presentation_path) as f:
                presentation_function = f.read()

            click.echo(f"Found presentation function for game '{game_name}'")

        game_config = GameConfig(
            name=game_name,
            code=game_code,
            presentation_function=presentation_function,
        )
        game_configs.append(game_config)
    return game_configs


def build_benchmark_config(
    models: list[str],
    human: bool,
    judge: str,
    games: list[GameConfig],
    benchmark_id: str,
    seed: str,
    num_rounds_per_game: int,
    num_maps_per_game: int,
):
    players = []
    if not human:
        players = [
            [
                PlayerConfig(
                    name="black",
                    id=model,
                    player_type="default",
                    options={
                        "model": model,
                        "provider": guess_provider_from_model(model),
                    },
                )
            ]
            for model in models
        ]
    else:
        players.append(
            [
                PlayerConfig(
                    name="black",
                    id="human",
                    player_type="human",
                    options={},
                )
            ]
        )

    return XegaBenchmarkConfig(
        config_type="short_benchmark_config",
        games=games,
        players=players,
        benchmark_id=benchmark_id,
        judge_model=judge,
        npc_players=DEFAULT_XEGA_CONFIG["npc_players"],
        num_rounds_per_game=num_rounds_per_game,
        num_variables_per_register=DEFAULT_XEGA_CONFIG["num_variables_per_register"],
        seed=seed,
        num_maps_per_game=num_maps_per_game,
    )


def add_player_to_expanded_config(
    config: ExpandedXegaBenchmarkConfig, new_player: PlayerConfig
) -> ExpandedXegaBenchmarkConfig:
    """Add a new player to an expanded benchmark config"""
    # Get unique games from the existing config
    unique_games = {}
    for game_config in config["games"]:
        game_key = (
            game_config["game"]["name"],
            game_config["game"]["code"],
            game_config["map_seed"],
        )
        if game_key not in unique_games:
            unique_games[game_key] = (game_config["game"], game_config["map_seed"])

    # Create new game configs for the new player
    new_game_configs = []
    for game, map_seed in unique_games.values():
        new_game_config: XegaGameConfig = {
            # Copy metadata fields
            "judge_model": config["judge_model"],
            "npc_players": config["npc_players"],
            "num_variables_per_register": config["num_variables_per_register"],
            "num_rounds_per_game": config["num_rounds_per_game"],
            "seed": config["seed"],
            "num_maps_per_game": config["num_maps_per_game"],
            # Game-specific fields
            "game": deepcopy(game),
            "players": [new_player],
            "map_seed": map_seed,
        }
        new_game_configs.append(new_game_config)

    # Create new expanded config with all games
    new_config = deepcopy(config)
    new_config["games"].extend(new_game_configs)

    return new_config


def remove_player_from_expanded_config(
    config: ExpandedXegaBenchmarkConfig, player_id_to_remove: str
) -> ExpandedXegaBenchmarkConfig:
    """Remove a player from an expanded benchmark config."""
    new_config = deepcopy(config)

    # Filter the games, removing any associated with the specified player ID.
    # In an expanded config, each game entry has exactly one player.
    original_game_count = len(new_config["games"])
    new_config["games"] = [
        game_config
        for game_config in new_config["games"]
        if game_config["players"][0]["id"] != player_id_to_remove
    ]

    # Notify the user if the specified player was not found in the config
    if len(new_config["games"]) == original_game_count:
        click.echo(
            f"Warning: Player with ID '{player_id_to_remove}' not found.", err=True
        )
    else:
        click.echo(f"Successfully removed player: {player_id_to_remove}")

    return new_config


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--output", help="Output configuration path", default="./xega_config.json"
)
@click.option(
    "--game-dir",
    help='Path to directory containing games in files ending with ".xega"',
)
@click.option(
    "--model",
    multiple=True,
    default=["gpt-4o"],
    help="Add a model as a player (can be used multiple times)",
)
@click.option(
    "--human",
    is_flag=True,
    help="Specify a human cli player. This overrides the --model flag and specifies only a single human player. This should be used for testing, in particular to play the game from the perspective of an agent",
)
@click.option(
    "--judge",
    default=DEFAULT_XEGA_CONFIG["judge_model"],
    help="Specify the judge model to use for the benchmark. Default is 'gpt2'",
)
@click.option(
    "--benchmark-id",
    default=None,
    help="Specify benchmark id for configuration. A unique id will be generated by default if not specified",
)
@click.option(
    "--num-rounds-per-game",
    default=DEFAULT_XEGA_CONFIG["num_rounds_per_game"],
    help="Specify the number of rounds to play per game mape. Default is 30",
)
@click.option(
    "--seed",
    default=DEFAULT_XEGA_CONFIG["seed"],
    help="Specify a seed for benchmark randomization. 'notrandom' is the default seed if not specified",
)
@click.option(
    "--num-maps-per-game",
    default=DEFAULT_XEGA_CONFIG["num_maps_per_game"],
    help="Specify the number of maps per game. Default is 1.",
    type=int,
)
@click.option(
    "--expand-config",
    is_flag=True,
    help="Fully expand the benchmark. This will generate a much more verbose configuration. This is useful for generating reproducible benchmarks, but the output will be much larger and more difficult to modify manually",
)
@click.option(
    "--print-config",
    is_flag=True,
    help="Print the configuration to stdout instead of writing to a file",
)
def configure(
    ctx: click.Context,
    output: str,
    game_dir: str,
    model: list[str],
    human: bool,
    judge: str,
    benchmark_id: str | None,
    num_rounds_per_game: int,
    seed: str,
    num_maps_per_game: int,
    print_config: bool,
    expand_config: bool,
):
    """Build Xega benchmark configuration"""
    # If a subcommand is invoked, let it handle the operation
    if ctx.invoked_subcommand is not None:
        return

    # Original behavior when called without subcommand
    if benchmark_id is None:
        benchmark_id = generate_benchmark_id()

    if not game_dir:
        games = [
            GameConfig(
                name="simple_game",
                code=SIMPLE_GAME_CODE,
                presentation_function=get_single_presentation(),
            )
        ]
    else:
        games = games_from_dir(game_dir)

    config = build_benchmark_config(
        model,
        human,
        judge,
        games,
        benchmark_id,
        seed,
        num_rounds_per_game,
        num_maps_per_game,
    )

    if expand_config:
        config = expand_benchmark_config(config)

    config_str = dumps(config, indent=2)
    if print_config:
        print(config_str)
    else:
        with open(output, "w") as f:
            f.write(config_str)
            print(f"Config written to {output}")


@configure.command("add-player")
@click.argument(
    "config_path",
    type=click.Path(exists=True, readable=True),
    default="./xega_config.json",
)
@click.option(
    "--model",
    "-m",
    multiple=True,
    required=True,
    help="Model to add as a player (can be used multiple times)",
)
@click.option(
    "--output",
    "-o",
    help="Output configuration path. If not specified, overwrites the input file.",
)
def add_player_cmd(
    config_path: str,
    model: list[str],
    output: str | None,
):
    """Add players to an existing expanded Xega benchmark configuration"""

    # Load the existing config
    with open(config_path) as f:
        config = json.load(f)

    # Verify it's an expanded config
    if config.get("config_type") != "expanded_benchmark_config":
        click.echo(
            "Error: This command only works with expanded configurations.", err=True
        )
        click.echo(
            "Use --expand-config when creating the configuration or convert it first.",
            err=True,
        )
        raise click.Abort()

    # Add each model as a new player
    for model_name in model:
        new_player = PlayerConfig(
            name="black",
            id=model_name,
            player_type="default",
            options={
                "model": model_name,
                "provider": guess_provider_from_model(model_name),
            },
        )
        config = add_player_to_expanded_config(config, new_player)
        click.echo(f"Added player: {model_name}")

    # Output
    config_str = dumps(config, indent=2)
    output_path = output or config_path

    with open(output_path, "w") as f:
        f.write(config_str)

    if output_path == config_path:
        click.echo(f"Updated config in place: {output_path}")
    else:
        click.echo(f"Updated config written to: {output_path}")


@configure.command("remove-player")
@click.argument(
    "config_path",
    type=click.Path(exists=True, readable=True),
    default="./xega_config.json",
)
@click.option(
    "--model",
    "-m",
    multiple=True,
    required=True,
    help="Model ID to remove as a player (can be used multiple times).",
)
@click.option(
    "--output",
    "-o",
    help="Output configuration path. If not specified, overwrites the input file.",
)
def remove_player_cmd(
    config_path: str,
    model: list[str],
    output: str | None,
):
    """Remove players from an existing expanded Xega benchmark configuration."""

    # Load the existing config
    with open(config_path) as f:
        config = json.load(f)

    # Verify it's an expanded config
    if config.get("config_type") != "expanded_benchmark_config":
        click.echo(
            "Error: This command only works with expanded configurations.", err=True
        )
        click.echo(
            "Use --expand-config when creating the configuration or convert it first.",
            err=True,
        )
        raise click.Abort()

    # Remove each specified player model
    for model_name in model:
        config = remove_player_from_expanded_config(config, model_name)

    # Output
    config_str = dumps(config, indent=2)
    output_path = output or config_path

    with open(output_path, "w") as f:
        f.write(config_str)

    if output_path == config_path:
        click.echo(f"Updated config in place: {output_path}")
    else:
        click.echo(f"Updated config written to: {output_path}")
