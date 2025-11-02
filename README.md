<div align="center">

# Xent Benchmark
[![Xent.ai](https://img.shields.io/badge/Xent-Labs-blue)](https://xent.ai) [![arXiv](https://img.shields.io/badge/arXiv-Xent-b31b1b.svg)](https://arxiv.org/abs/2506.06832) [![Twitter](https://img.shields.io/badge/twitter-x?logo=x&logoColor=white&color=%230f1419)](https://x.com/HonglerClement)

<div align="center" style="font-family: Arial, sans-serif;">
  <p>
    <a href="#about" style="text-decoration: none; font-weight: bold;">About</a> •
    <a href="#leaderboard" style="text-decoration: none; font-weight: bold;">Leaderboard</a> •
    <a href="#run" style="text-decoration: none; font-weight: bold;">Run</a> •
    <a href="#develop" style="text-decoration: none; font-weight: bold;">Develop</a> •
    <a href="#license" style="text-decoration: none; font-weight: bold;">License</a> •
    <a href="#cite" style="text-decoration: none; font-weight: bold;">Cite</a>
  </p>
</div>

</div>

## About

Welcome to the Xent Benchmark Github 🥳

Some quick notes:
- Check out our website: [xent.ai](https://xent.ai)
- View our paper: [arXiv](https://arxiv.org/abs/2506.06832)

## Leaderboard

See more in depth results at [xent.ai](https://xent.ai/leaderboard)

| Rank | Player ID | Score |
|:----:|:----------|------:|
| 1 | gemini-2.5-pro | 65.86 |
| 2 | grok-4-0709 | 63.22 |
| 3 | gpt-5 | 62.77 |
| 4 | deepseek-reasoner | 62.67 |
| 5 | gemini-2.5-flash | 59.08 |
| 6 | claude-opus-4-1-20250805 | 58.65 |
| 7 | claude-opus-4-20250514 | 58.35 |
| 8 | gpt-5-mini | 49.22 |
| 9 | claude-sonnet-4-20250514 | 48.45 |
| 10 | kimi-k2-0905-preview | 42.89 |
| 11 | deepseek-chat | 35.48 |
| 12 | gpt-5-nano | 23.27 |


## Run

So how do you run a Xent benchmark? There are two main ways: a local web interface and the CLI. There are instructions for both below.

But first, you'll need to install the package: `pip install xent`

If you want to run from source, then you need to have [uv](https://github.com/astral-sh/uv) installed. See the [installation instructions](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or just run `curl -LsSf https://astral.sh/uv/install.sh | sh`. If using `uv`, when following the instructions below you'll need to call `uv run xent` instead of just `xent`.

### Web Interface

To start the web interface, call `xent serve`. This starts a webserver running on localhost:8000 and opens a browser window to that page.

#### Playing Games

At the top of the page, you'll see a "Play Game" button. This allows you to play games directly, rather than benchmarking llms / agents.

Once you are on the play page, you can specify the game you want to execute by pasting the code into the game code panel. When you begin, the judge model (gpt2) will execute locally and you can begin trying out game execution and seeing results. Let us know if you write any fun games and we will happily add them to this repository!

#### Benchmark Configuration

If you want to run a benchmark, the first thing you need to do is set up configuration for that benchmark.

**Basic Settings**: in this panel, you can configure settings that apply for the entire benchmark, such as Judge model, how many rounds per game, and how many maps per game.

**Players**: here you can configure what players you want for your model. See "Customized Model Configuration" below for information on how you can specify more information about llm players via query parameters on model specification. You can also specify a human player for interactive mode.

**Games**: choose to either use the default games that come packaged with `xent`, or write custom games (as well as their presentation functions).

Once ready, click "Create Benchmark Configuration" to generate your config.

#### Benchmark Execution

Once you have saved a benchmark, you can now execute it. From the configuration dashboard page, you can use the "Start Benchmark" button to begin local execution.

Depending on your configuration, benchmark execution can be fairly time consuming. Once the benchmark has begun execution, you will see completed games as they finish, but this can take anywhere from 2 to 20 minutes, so be patient!

Please look at "Environment variables" below to find out about what information you will need to have available in order to let execution complete successfully.


### CLI

#### Benchmark Configuration

First, we'll create a configuration for your benchmark run. This configuration will contain things like:
- Games to execute
- Maps for the different games
- Players for those games
- Model to use as a judge

To generate such a configuration you call `uv run xent configure`.

```bash
# Generate a minimal configuration with a simple game played by gpt-4o
xent configure
# Generate a configuration with a simple game played by gpt-4.1 and o3
xent configure --model gpt-4.1 --model o3
# Generate a configuration from specific game files and/or directories
uv run xent configure --game-dir ./games
# See more CLI configuration options
uv run xent configure --help
```

The configuration will be stored in a json file (`./xent_config.json` by default) which can be passed to `xent run` for execution. To better understand the configuration file, take a look at `CondensedXentBenchmarkConfig` and `ExpandedXentBenchmarkConfig` in `src/xent/common/configuration_types.py`

So, now that we have a configuration, how do we run it?

#### Benchmark Execution

To run a benchmark from the command line, use `xent run`. But before you do that, here are some notes:

By default, `xent run` will use `./xent_config.json` as the path to the benchmark configuration. You can change this by doing `uv run xent run --config path/to/config.json`. To see more information on available flags, call `xent run --help`.

During execution, `xent run` will place results and execution artifacts into a directory. By default this is `./results/<benchmark id>`. You can modify that path via `uv run xent run --results-dir path/to/results`. Xent will create a new directory in the specified path with the benchmark_id.

In order to be somewhat robust to failure or interruption, Xent will look into the results directory for completed work. So if you re-run an already completed benchmark, it will effectively be a no-op. Instead you can pass either `--regenerate-id` (which will make a new, timestamped, benchmark id for the run) or `--clean` which will destroy any existing data in the results dir. Be careful using `--clean`! You can totally delete your valuable results! I recommend using `--regenerate-id`


##### Environment variables

A brief note about environment variables.  If you want to run a Xent benchmark using paid APIs (eg ChatGPT), then you will need to export an environment variable holding your API key. Currently, Xent supports:

- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- GROK_API_KEY
- DEEPSEEK_API_KEY
- MOONSHOT_API_KEY

You'll get an exception if you try to call these models without the proper environment variables.

#### Benchmark Results

Now that you have completed a benchmark execution, its time to examine the results. The easiest way to look at the results is to read the generated markdown report. This will be present in `results_directory/<benchmark_id>/report.md`. It contains a human-readable summary (including some nice charting) of all the games played.

In addition to report.md, there is also the `benchmark_<benchmark_id>.json` file. This contains the complete data generated by the benchmark and its structure is defined in `src/xent/common/configuration_types.py` as `BenchmarkResult`.

You'll also see files named "game_<game_name>_<model_name>.json". These files contain results for that game-player pair (as well as the original configuration of the game). The data structure is the `GameMapResults` type defined in `src/xent/common/configuration_types.py`. All of the data in these files will be present in the benchmark json, but you may find it handy to inspect them individually as the output can be quite long.

Finally, there is log.txt which is simply the log output of the benchmark execution. Any errors or issues will be visible here.

## Advanced Configuration

The following is a guide for those of you who you are interested in evaluating with customized model configuration or even with a custom agent.

### Customized Model Configuration

By default, Xent uses configuration options when calling models. For LLM APIs (eg ChatGPT) Xent tends to have very little usage of configuration such as temperature parameters. For models called via HuggingFace, however, more configuration is necessary.

When calling `xent configure --model foo`, you can use query parameters to specify params that will be forwarded directly to the api request. For example `xent configure --model gpt-5?reasoning_effort=high` will pass `reasoning_effort: "high"` into the openai requests made for that model.

You can view the model configuration options available in `src/xent/runtime/player_configuration.py`. These options (`DefaultXGPOptions` and `DefaultHFXGPOptions`) are specified in the `options` field of `PlayerConfig` type defined in `src/xent/common/configuration_types.py`. You can view the actual usage of these options in the `HuggingFaceClient` class defined in `src/xent/runtime/llm_api_client.py`.

### Adding Custom Agents

Some people modifying Xent are interested in running Xent against their own agents. If that's you, then here is some good news! We have endeavored to make this relatively simple as long as you are familiar with python development.

Here are the key places you should look at to make those changes:

- **`src/xent/runtime/players/base_player.py`** - This contains the XGP interface that player agents must implement.
- **`src/xent/runtime/players/default_players.py`** - This contains the default player agent implementation. You can use this as a reference implementation.
- **`src/xent/runtime/players/players.py`** - This contains the registry and mapping between player types and player implementations.

By making changes to a few files, you can add your own agent implementation to the Xent system and begin benchmarking it yourself. If you have spent the time to do so, then we encourage you to open a pull request with your changes so that others can benefit from your work.

## Develop

A short guide to get you started modifying Xent and maybe (hopefully!) contributing.

### Getting Started

1. Before you begin, ensure you have the following installed:
- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

2. Run the CLI tool
```bash
uv run xent
```

4. Run tests

> **Note:** Running tests will execute GPT-2 via Hugging Face. If you run integration tests, then you'll need to have Ollama running locally with qwen3:0.6b available.

```bash
# Run all tests
uv run pytest
# Run only unit tests
uv run pytest -m "not integration"
# Run only integration tests
uv run pytest -m integration
```

### Code Quality Tools

The project uses modern Python tooling for consistent code quality:

#### Quick Commands

```bash
# Format code
uv run ruff format .

# Lint and auto-fix issues
uv run ruff check --fix .

# Type check (source only)
uv run mypy src/

# Run all quality checks
uv run ruff format . && uv run ruff check --fix . && uv run mypy src/
```

#### Pre-commit Hooks

Pre-commit hooks are available and will automatically:
- Format code with Ruff
- Fix auto-fixable linting issues
- Run type checking on staged files

To run pre-commit manually:
```bash
uv run pre-commit run --all-files
```

#### VSCode Integration

Project-specific VSCode settings are configured to:
- Use Ruff for formatting and linting
- Format on save
- Organize imports automatically
- Integrate with the project's Python interpreter

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Cite

The code in this repository is developed from the paper below. Please cite it if you find the repository helpful.

```
@misc{hongler2025crossentropygameslanguagemodels,
      title={Cross-Entropy Games for Language Models: From Implicit Knowledge to General Capability Measures},
      author={Clément Hongler and Andrew Emil},
      year={2025},
      eprint={2506.06832},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2506.06832},
}
```
