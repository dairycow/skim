"""CLI entry point for the ASX analysis tool."""

from skim.analysis.cli.cli import CLI


def main():
    """Main entry point for the analysis CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
