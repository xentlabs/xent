import click

from xega.cli.configure import configure
from xega.cli.analyze import analyze
from xega.cli.run import run


@click.group()
def main():
    """XEGA LLM Benchmark Tool"""
    pass


main.add_command(run)
main.add_command(analyze)
main.add_command(configure)