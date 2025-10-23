from importlib.metadata import PackageNotFoundError, version


def get_xent_version() -> str:
    try:
        return version("xent")
    except PackageNotFoundError:
        # Package is not installed (likely in development/editable mode)
        return "0.3.0-dev"


def validate_version(
    config_version: str | None, current_version: str
) -> tuple[bool, str]:
    if config_version is None:
        return (
            True,
            "Warning: Configuration has no version field (likely created with older xent version)",
        )

    if config_version == current_version:
        return True, f"Version match: {current_version}"

    return (
        False,
        f"Version mismatch: configuration was created with xent {config_version}, "
        f"but current version is {current_version}",
    )
