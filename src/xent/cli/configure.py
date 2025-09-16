import json
from pathlib import Path
from typing import Any

import click

from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.cli.cli_util import generate_benchmark_id
from xent.common.configuration_types import (
    CondensedXentBenchmarkConfig,
    ExpandedXentBenchmarkConfig,
    ExpansionConfig,
    GameConfig,
    PlayerConfig,
    XentMetadata,
)
from xent.common.constants import SIMPLE_GAME_CODE
from xent.common.util import dumps
from xent.common.version import get_xent_version
from xent.presentation.executor import get_default_presentation, get_single_presentation
from xent.runtime.llm_api_client import guess_provider_from_model

DEFAULT_XENT_METADATA = XentMetadata(
    benchmark_id="",
    xent_version=get_xent_version(),
    judge_model="gpt2",
    num_rounds_per_game=30,
    seed="notrandom",
)

DEFAULT_EXPANSION_CONFIG = ExpansionConfig(num_maps_per_game=1)


def game_from_file(game_file_path: Path) -> GameConfig:
    game_name = game_file_path.stem
    game_code = game_file_path.read_text()

    presentation_function = get_default_presentation()
    presentation_path = game_file_path.with_name(f"{game_name}_presentation.py")
    try:
        presentation_function = presentation_path.read_text()
    except FileNotFoundError:
        click.echo(f"No presentation function found for game '{game_name}'")

    return GameConfig(
        name=game_name, code=game_code, presentation_function=presentation_function
    )


def games_from_paths(paths: list[Path]) -> list[GameConfig]:
    all_game_paths: set[Path] = set()
    for p in paths:
        if p.is_dir():
            all_game_paths.update(p.glob("*.xent"))
        elif p.is_file():
            if p.suffix != ".xent":
                raise click.BadParameter(f"Not a .xent file: {p}")
            all_game_paths.add(p)
        else:
            raise click.BadParameter(f"Path does not exist: {p}")

    # Two paths that point to the same file should be considered the same
    all_game_paths = {p.resolve() for p in all_game_paths}

    return [game_from_file(p) for p in all_game_paths]


def build_benchmark_config(
    models: list[str],
    human: bool,
    judge: str,
    games: list[GameConfig],
    benchmark_id: str,
    seed: str,
    num_rounds_per_game: int,
    num_maps_per_game: int,
) -> CondensedXentBenchmarkConfig:
    players = []
    if not human:
        players = [
            PlayerConfig(
                name="black",
                id=model,
                player_type="default",
                options={
                    "model": model,
                    "provider": guess_provider_from_model(model),
                },
            )
            for model in models
        ]
    else:
        players.append(
            PlayerConfig(
                name="black",
                id="human",
                player_type="human",
                options={},
            )
        )

    return CondensedXentBenchmarkConfig(
        config_type="condensed_xent_config",
        games=games,
        players=players,
        metadata=XentMetadata(
            benchmark_id=benchmark_id,
            xent_version=get_xent_version(),
            judge_model=judge,
            num_rounds_per_game=num_rounds_per_game,
            seed=seed,
        ),
        expansion_config=ExpansionConfig(num_maps_per_game=num_maps_per_game),
    )


def add_player_to_config(
    config: ExpandedXentBenchmarkConfig, new_player: PlayerConfig
) -> ExpandedXentBenchmarkConfig:
    """Add a new player to an expanded benchmark config"""
    players = config["players"]
    if any(p["id"] == new_player["id"] for p in players):
        print("Player already exists in benchmark configuration!")
        return config
    players.append(new_player)
    config["players"] = players
    return config


def remove_player_from_config(
    config: ExpandedXentBenchmarkConfig, player_id_to_remove: str
) -> ExpandedXentBenchmarkConfig:
    players = config["players"]
    if not any(p["id"] == player_id_to_remove for p in players):
        print("Player not found benchmark configuration!")
        return config

    new_players = [p for p in players if p["id"] != player_id_to_remove]
    config["players"] = new_players
    return config


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--output", help="Output configuration path", default="./xent_config.json"
)
@click.option(
    "--game-path",
    "--game-dir",
    "game_paths",
    multiple=True,
    type=click.Path(exists=True, readable=True),
    help="Path(s) to .xent game file(s). If a directory is provided, include all .xent files in the directory. Repeat to add multiple.",
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
    default=DEFAULT_XENT_METADATA["judge_model"],
    help="Specify the judge model to use for the benchmark. Default is 'gpt2'",
)
@click.option(
    "--benchmark-id",
    default=None,
    help="Specify benchmark id for configuration. A unique id will be generated by default if not specified",
)
@click.option(
    "--num-rounds-per-game",
    default=DEFAULT_XENT_METADATA["num_rounds_per_game"],
    help="Specify the number of rounds to play per game mape. Default is 30",
)
@click.option(
    "--seed",
    default=DEFAULT_XENT_METADATA["seed"],
    help="Specify a seed for benchmark randomization. 'notrandom' is the default seed if not specified",
)
@click.option(
    "--num-maps-per-game",
    default=DEFAULT_EXPANSION_CONFIG["num_maps_per_game"],
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
    game_paths: list[str],
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
    """Build Xent benchmark configuration"""
    # If a subcommand is invoked, let it handle the operation
    if ctx.invoked_subcommand is not None:
        return

    # Original behavior when called without subcommand
    if benchmark_id is None:
        benchmark_id = generate_benchmark_id()

    if not game_paths:
        games = [
            GameConfig(
                name="simple_game",
                code=SIMPLE_GAME_CODE,
                presentation_function=get_single_presentation(),
            )
        ]
    else:
        games = games_from_paths([Path(p) for p in game_paths])

    config: Any = build_benchmark_config(
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
        print(
            f"Configuration expanded with xent version {config.get('xent_version', 'unknown')}"
        )

    config_str = dumps(config, indent=2)
    if print_config:
        print(config_str)
    else:
        with open(output, "w") as f:
            f.write(config_str)
            current_version = get_xent_version()
            if expand_config:
                print(f"Config written to {output} (xent version: {current_version})")
            else:
                print(f"Config written to {output}")
                print(
                    f"Note: Configuration will be stamped with xent version {current_version} when expanded/run"
                )


@configure.command("add-player")
@click.argument(
    "config_path",
    type=click.Path(exists=True, readable=True),
    default="./xent_config.json",
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
    """Add players to an existing expanded Xent benchmark configuration"""

    # Load the existing config
    with open(config_path) as f:
        config = json.load(f)

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
        config = add_player_to_config(config, new_player)
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
    default="./xent_config.json",
)
@click.option(
    "--player-id",
    "-p",
    multiple=True,
    required=True,
    help="Player ID to remove as a player (can be used multiple times).",
)
@click.option(
    "--output",
    "-o",
    help="Output configuration path. If not specified, overwrites the input file.",
)
def remove_player_cmd(
    config_path: str,
    player_id: list[str],
    output: str | None,
):
    """Remove players from an existing expanded Xent benchmark configuration."""

    # Load the existing config
    with open(config_path) as f:
        config = json.load(f)

    # Verify it's an expanded config
    if config.get("config_type") != "expanded_xent_config":
        click.echo(
            "Error: This command only works with expanded configurations.", err=True
        )
        click.echo(
            "Use --expand-config when creating the configuration or convert it first.",
            err=True,
        )
        raise click.Abort()

    # Remove each specified player id
    for pid in player_id:
        config = remove_player_from_config(config, pid)
        print(f"Successfully removed player: {pid}")

    # Output
    config_str = dumps(config, indent=2)
    output_path = output or config_path

    with open(output_path, "w") as f:
        f.write(config_str)

    if output_path == config_path:
        click.echo(f"Updated config in place: {output_path}")
    else:
        click.echo(f"Updated config written to: {output_path}")
