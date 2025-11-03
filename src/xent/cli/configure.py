import contextlib
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs

import click

from xent.benchmark.expand_benchmark import expand_benchmark_config
from xent.cli.cli_util import generate_benchmark_id
from xent.common.configuration_types import (
    CondensedXentBenchmarkConfig,
    ExpandedXentBenchmarkConfig,
    ExpansionConfig,
    GameConfig,
    PlayerConfig,
    TextGeneratorType,
    XentMetadata,
)
from xent.common.errors import XentConfigurationError
from xent.common.game_discovery import discover_games_in_paths, discover_packaged_games
from xent.common.util import dumps
from xent.common.version import get_xent_version
from xent.runtime.players.llm_api_client import guess_provider_from_model

DEFAULT_XENT_METADATA = XentMetadata(
    benchmark_id="",
    xent_version=get_xent_version(),
    judge_model="gpt2",
    num_rounds_per_game=30,
    seed="notrandom",
    store_full_player_interactions=False,
    npcs=[],
)

DEFAULT_EXPANSION_CONFIG = ExpansionConfig(
    num_maps_per_game=1,
    text_generation_config={
        "generator_type": "JUDGE",
        "generator_config": {},
        "max_length": 50,
    },
)


def parse_model_spec(spec: str) -> tuple[str, dict[str, Any]]:
    """Parse a model specification with optional URL-like parameters.

    Examples:
        'gpt-4o' -> ('gpt-4o', {})
        'gpt-4o?temperature=0.7&reasoning_effort=high' -> ('gpt-4o', {'temperature': 0.7, 'reasoning_effort': 'high'})
    """
    if "?" in spec:
        model, query = spec.split("?", 1)
        params = {}
        for key, values in parse_qs(query).items():
            value = values[0]  # Take first value
            # Type inference - try to parse as JSON to get numbers, bools, null
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                value = json.loads(value)
            params[key] = value

        return model, params
    return spec, {}


def build_benchmark_config(
    models: list[str],
    human: bool,
    judge: str,
    games: list[GameConfig],
    benchmark_id: str,
    seed: str,
    num_rounds_per_game: int,
    num_maps_per_game: int,
    text_generation_mode: str,
    corpus_path: str,
    store_full_interaction,
) -> CondensedXentBenchmarkConfig:
    players = []
    if not human:
        for model_spec in models:
            model, request_params = parse_model_spec(model_spec)
            player_options: dict[str, Any] = {
                "model": model,
                "provider": guess_provider_from_model(model),
            }
            if request_params:
                player_options["request_params"] = request_params

            players.append(
                PlayerConfig(
                    name="black",
                    id=model,
                    player_type="default",
                    options=player_options,
                )
            )
    else:
        players.append(
            PlayerConfig(
                name="black",
                id="human",
                player_type="human",
                options={},
            )
        )

    generator_config: Any = {}
    generation_max_length = 50
    if text_generation_mode == "COMMUNITY_ARCHIVE":
        generator_config = {
            "path_to_archive": corpus_path,
            "mode": "SEQUENTIAL",
            "seed": "seed",
        }
        generation_max_length = -1
    elif text_generation_mode != "JUDGE":
        raise XentConfigurationError(
            f"Invalid text generation mode specified: {text_generation_mode}"
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
            store_full_player_interactions=store_full_interaction,
            npcs=[],
        ),
        expansion_config=ExpansionConfig(
            num_maps_per_game=num_maps_per_game,
            text_generation_config={
                "generator_type": cast(TextGeneratorType, text_generation_mode),
                "generator_config": generator_config,
                "max_length": generation_max_length,
            },
        ),
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
    help="Add a model as a player with optional parameters using URL-like syntax. "
    "Examples: 'gpt-4o', 'gpt-4o?temperature=0.7&reasoning_effort=high', "
    "'claude-3-5-sonnet?max_tokens=8192'. Can be used multiple times.",
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
    "--text-generation-mode",
    default=DEFAULT_EXPANSION_CONFIG["text_generation_config"]["generator_type"],
    help="Specify the generation mode for map creation",
)
@click.option(
    "--corpus-path",
    default="",
    help="Path to corpus for text generation. Only used --text-generation-mode is COMMUNITY_ARCHIVE",
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
    "--store-full-interaction",
    is_flag=True,
    help="Store the full player interactions in benchmark results. Specificially, this will record the prompting and full model response (including thinking and other tokens) into the event history",
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
    text_generation_mode: str,
    corpus_path: str,
    benchmark_id: str | None,
    num_rounds_per_game: int,
    seed: str,
    num_maps_per_game: int,
    print_config: bool,
    store_full_interaction: bool,
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
        # Default to games packaged with xent
        games = discover_packaged_games()
    else:
        games = discover_games_in_paths([Path(p) for p in game_paths])

    config: Any = build_benchmark_config(
        model,
        human,
        judge,
        games,
        benchmark_id,
        seed,
        num_rounds_per_game,
        num_maps_per_game,
        text_generation_mode,
        corpus_path,
        store_full_interaction,
    )

    if expand_config:
        config = expand_benchmark_config(config)
        print(
            f"Configuration expanded with xent version {config['metadata']['xent_version']}"
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
    help="Model to add as a player with optional parameters using URL-like syntax. "
    "Examples: 'gpt-4o', 'gpt-4o?temperature=0.7&reasoning_effort=high'. "
    "Can be used multiple times.",
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
    for model_spec in model:
        model_name, request_params = parse_model_spec(model_spec)
        player_options: dict[str, Any] = {
            "model": model_name,
            "provider": guess_provider_from_model(model_name),
        }
        if request_params:
            player_options["request_params"] = request_params

        new_player = PlayerConfig(
            name="black",
            id=model_name,
            player_type="default",
            options=player_options,
        )
        config = add_player_to_config(config, new_player)
        if request_params:
            click.echo(f"Added player: {model_name} with params: {request_params}")
        else:
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
