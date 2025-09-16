from importlib.metadata import PackageNotFoundError, version


def get_xega_version() -> str:
    try:
        return version("xega")
    except PackageNotFoundError:
        # Package is not installed (likely in development/editable mode)
        return "0.1.0-dev"


def validate_version(
    config_version: str | None, current_version: str
) -> tuple[bool, str]:
    if config_version is None:
        return (
            True,
            "Warning: Configuration has no version field (likely created with older xega version)",
        )

    if config_version == current_version:
        return True, f"Version match: {current_version}"

    return (
        False,
        f"Version mismatch: configuration was created with xega {config_version}, "
        f"but current version is {current_version}",
    )
