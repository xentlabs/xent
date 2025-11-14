import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "xent"


@dataclass(frozen=True)
class BenchmarkPaths:
    """Paths specific to a single benchmark run."""

    benchmark_dir: Path
    logs_dir: Path


def _env_path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v).expanduser() if v else default


def data_root() -> Path:
    """Return the base directory for all Xent user data.

    Order of precedence:
    1) XENT_DATA_DIR environment variable
    2) platform-specific user data directory for the application
    """

    dirs = PlatformDirs(appname=APP_NAME, appauthor=False)
    return _env_path("XENT_DATA_DIR", Path(dirs.user_data_dir))


def results_root() -> Path:
    """Return the root directory for benchmark results.

    Order of precedence:
    1) XENT_RESULTS_DIR environment variable
    2) <data_root>/benchmarks
    """

    override = os.getenv("XENT_RESULTS_DIR")
    if override:
        return Path(override).expanduser()
    return data_root() / "benchmarks"


def benchmark_dir(benchmark_id: str) -> Path:
    """Return the directory for a specific benchmark's artifacts."""

    return results_root() / benchmark_id


def logs_dir(benchmark_id: str) -> Path:
    """Return the logs directory for a specific benchmark."""

    return benchmark_dir(benchmark_id) / "logs"


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) if it does not exist, return the path."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_benchmark_dirs(benchmark_id: str) -> BenchmarkPaths:
    """Ensure the benchmark and logs directories exist and return their paths."""

    bdir = ensure_dir(benchmark_dir(benchmark_id))
    ldir = ensure_dir(bdir / "logs")
    return BenchmarkPaths(benchmark_dir=bdir, logs_dir=ldir)
