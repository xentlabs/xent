<div align="center">

# Xega Benchmark
[![Xent.Tech](https://img.shields.io/badge/Xent-Tech-blue)](https://xent.tech) [![arXiv](https://img.shields.io/badge/arXiv-Xega-b31b1b.svg)](https://arxiv.org/abs/2506.06832) [![Twitter](https://img.shields.io/badge/twitter-x?logo=x&logoColor=white&color=%230f1419)](https://x.com/HonglerClement)

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

Welcome to the Xega (XentGame) Benchmark Github 🥳

Some quick notes:
- Check out our website: [Xent.Tech](https://xent.tech)
- View our paper: [arXiv](https://arxiv.org/abs/2506.06832)
- Improved support for library usage of Xega coming soon

## Leaderboard

See more in depth results at [xent.tech](https://xent.tech/leaderboard)

| Rank | Player ID | Score |
|:----:|:----------|------:|
| 1 | o3 | 2224.82 |
| 2 | grok-4-0709 | 2020.63 |
| 3 | deepseek-reasoner | 1785.18 |
| 4 | claude-sonnet-4-20250514 | 1621.19 |
| 5 | gemini-2.5-flash | 1608.86 |
| 6 | claude-opus-4-20250514 | 1599.26 |
| 7 | claude-3-7-sonnet-20250219 | 1574.04 |
| 8 | o4-mini | 1470.44 |
| 9 | claude-3-5-sonnet-20241022 | 1359.36 |
| 10 | gpt-4.1 | 1308.66 |
| 11 | gemini-2.5-pro | 1304.17 |
| 12 | grok-3 | 1234.02 |
| 13 | deepseek-chat | 1204.86 |
| 14 | gpt-4o | 1178.54 |
| 15 | grok-3-mini | 1072.38 |



## Run

So how do you run a Xega benchmark? Lets break it into steps

### Initial configuration

In order to run Xega, you need to have [uv](https://github.com/astral-sh/uv) installed. See the [installation instructions](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or just run `curl -LsSf https://astral.sh/uv/install.sh | sh` 


### Benchmark Configuration

First, we'll create a configuration for your benchmark run. This configuration will contain things like:
- Games to execute
- Players for those games
- Model to use as a judge
- Whether games should be played iteratively
- The maximum number of game-code lines to execute per game

To generate such a configuration you call `uv run xega configure`. 

```bash
# Generate a minimal configuration with a simple game played by gpt-4o
uv run xega configure
# Generate a configuration with a simple game played by gpt-4.1 and o3
uv run xega configure --model gpt-4.1 --model o3
# Generate a configuration from games defined in a directory
uv run xega configure --game-dir ./games
# See more CLI configuration options
uv run xega configure --help
```

The configuration will be stored in a json file (`./xega_config.json` by default) which can be passed to `xega run` for execution.

Of course, you don't have to use the CLI to generate this configuration. Take a look at `XegaBenchmarkConfig` in `src/xega/common/xega_types.py` to see exactly what options are available.

So, now that we have a configuration, how do we run it?

### Benchmark Execution

To run a benchmark simply `uv run xega run`. But before you do that, here are some notes:

By default, `xega run` will use `./xega_config.json` as the path to the benchmark configuration. You can change this by doing `uv run xega run --config path/to/config.json`

During execution, `xega run` will place results and execution artifacts into a directory. By default this is `./results/<benchmark id>`. You can modify that path via `uv run xega run --results-dir path/to/results`. Xega will create a new directory in the specified path with the benchmark_id.

In order to be somewhat robust to failure or interruption, Xega will look into the results directory for completed work. So if you re-run an already completed benchmark, it will effectively be a no-op. Instead you can pass either `--regenerate-id` (which will make a new, timestamped, benchmark id for the run) or `--clean` which will destroy any existing data in the results dir. Be careful using `--clean`! You can totally delete your valuable results! I recommend using `--regenerate-id`

#### Environment variables

A brief note about environment variables.  If you want to run a Xega benchmark using paid APIs (eg ChatGPT), then you will need to export an environment variable holding your API key. Currently, Xega supports:

- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
- GROK_API_KEY
- DEEPSEEK_API_KEY

You'll get an exception if you try to call these models without the proper environment variables.

### Benchmark Results

Now that you have completed a benchmark execution, its time to examine the results. The easiest way to look at the results is to read the generated markdown report. This will be present in `results_directory/<benchmark_id>/report.md`. It contains a human-readable summary (including some nice charting!) of all the games played.

In addition to report.md, there is also the `benchmark_<benchmark_id>.json` file. This contains the complete data generated by the benchmark and its structure is defined in `src/xega/common/xega_types.py` as `XegaBenchmarkResult`.

You'll also see files named "game_<game_name>_<model_name>.json". These files contain results for that game-player pair (as well as the original configuration of the game). The data structure is the `XegaGameResult` type defined in `src/xega/common/xega_types.py`. All of the data in these files will be present in the benchmark json, but you may find it handy to inspect them individually as the output can be quite long.

Finally, there is log.txt which is simply the log output of the benchmark execution. Any errors or issues will be visible here.

## Advanced Configuration

The following is a guide for those of you who you are interested in evaluating with customized model configuration or even with a custom agent.

### Customized Model Configuration

By default, Xega uses configuration options when calling models. For LLM APIs (eg ChatGPT) Xega tends to have very little usage of configuration such as temperature parameters. For models called via HuggingFace, however, more configuration is necessary.

You can view the model configuration options available in `src/xega/runtime/player_configuration.py`. These options (`DefaultXGPOptions` and `DefaultHFXGPOptions`) are specified in the `options` field of `PlayerConfig` type defined in `src/xega/common/xega_types.py`. You can view the actual usage of these options in the `HuggingFaceClient` class defined in `src/xega/runtime/llm_api_client.py`.

### Adding Custom Agents

I'm going to guess that most people modifying Xega are interested in running Xega against their own agents.
If that's you, then here is some good news! We have endeavored to make this relatively simple as long as you are familiar with python development.

Here are the key places you should look at to make those changes:

- **`src/xega/runtime/base_player.py`** - This contains the interface that player agents must implement. It also contains some guidance around adding new agents.
- **`src/xega/runtime/default_players.py`** - This contains the existing player agent implementation. You can use this as a reference implementation.
- **`src/xega/runtime/players.py`** - This contains the registry and mapping between player types and player implementations.

By making changes to a few files, you can add your own agent implementation to the Xega system and begin benchmarking it yourself. If you have spent the time to do so, then we encourage you to open a pull request with your changes so that others can benefit from your work.

## Develop

A short guide to get you started modifying Xega and maybe (hopefully!) contributing.

### Getting Started

1. Before you begin, ensure you have the following installed:
- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) for dependency management

2. Run the CLI tool
```bash
uv run xega
```

4. Run tests

> **Note:** Running tests will execute GPT-2 via Hugging Face. If you run integration tests, then you'll need to have Ollama running locally with qwen3:0.6b available.

```bash
# Run all tests
uv run pytest
# Run a specific test
uv run pytest tests/test_x_string.py
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

Pre-commit hooks are installed and will automatically:
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

### Future Work

A short list of features and changes that we are contemplating making.

- A system for emitting metrics during Xega benchmarking. These metrics could be both for actual results and observability. Such a system would allow for live charting of results as well as improved support for monitoring remote benchmark execution.
- More flexible agent registration, allowing for agent developers to do their development externally to the Xega project and then import Xega as a library for benchmark execution.
- Improved collection of agent responses, allowing users to easily and directly connect agent responses to game rewards
- Downloading of public xega benchmark leaderboard results, allowing for easy, private comparison against user results

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
