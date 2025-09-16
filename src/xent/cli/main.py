import click

from xent.cli.analyze import analyze
from xent.cli.configure import configure
from xent.cli.run import run
from xent.cli.serve import serve


@click.group()
def main():
    """XENT LLM Benchmark Tool"""
    pass


main.add_command(run)
main.add_command(analyze)
main.add_command(configure)
main.add_command(serve)
