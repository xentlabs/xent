import click

from xega.cli.analyze import analyze
from xega.cli.configure import configure
from xega.cli.run import run
from xega.cli.serve import serve


@click.group()
def main():
    """XEGA LLM Benchmark Tool"""
    pass


main.add_command(run)
main.add_command(analyze)
main.add_command(configure)
main.add_command(serve)
