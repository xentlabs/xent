import click

from xent.cli.analyze import analyze
from xent.cli.configure import configure
from xent.cli.run import run
from xent.cli.serve import serve
from xent.common.version import get_xent_version


@click.group()
@click.version_option(version=get_xent_version(), prog_name="xent")
def main():
    """XENT LLM Benchmark Tool"""
    pass


main.add_command(run)
main.add_command(analyze)
main.add_command(configure)
main.add_command(serve)
