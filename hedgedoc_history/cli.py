from importlib.metadata import version
from pathlib import Path
import sys

import click
import environs
from loguru import logger as log

from hedgedoc_history.main import (
    REFERENCE_ID,
    STRUCTURE_PATH,
    Config,
    generate_markdown,
    get_config,
    get_history,
    login,
    structure_history,
    upload_md_reference,
)

env = environs.Env()
env.read_env()


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(("TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
    default="INFO",
    help="Log level.",
)
@click.option("--debug/--no-debug", is_flag=True, default=False, help="Turn on logging.")
@click.option("--username", "-u", envvar="HD_USER", help="HedgeDoc username.")
@click.option("--password", "-p", envvar="HD_PASS", help="HedgeDoc password.")
@click.version_option(version(__package__))
@click.pass_context
def main(ctx, log_level: str, debug: bool, username: str, password: str) -> None:
    _setup_logger(log_level, enabled=debug)
    log.debug("Logging in")
    login(username, password)
    config = get_config()
    log.debug(f"Config: {config}")
    ctx.obj = config


def _setup_logger(level: str, enabled: bool = False) -> None:
    log.remove()
    if enabled is False:
        return
    log.add(sink=sys.stdout, level=level)


@click.option(
    "--only-pinned", is_flag=True, default=False, help="Only show pinned notes."
)
@main.command()
@click.pass_obj
def history(cfg: Config, only_pinned: bool) -> None:
    log.trace("Entered get_history")
    history = get_history()

    for entry in history:
        if only_pinned and entry.pinned is False:
            continue

        line = f"{cfg.server}/{entry.id} - '{entry.text}' ({entry.tags})"
        click.echo(line)


@main.command()
@click.option(
    "--structure",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    default=STRUCTURE_PATH,
)
@click.pass_obj
def structure(cfg: Config, structure: Path) -> None:
    log.trace("Parsing structure")
    struct_cfg = structure_history(cfg, structure)
    for it in struct_cfg.items:
        click.echo(f"{'  ' * it.level}- {it.name} ({it.tags})")


@click.option(
    "--structure",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    default=STRUCTURE_PATH,
)
@click.option(
    "--only-pinned", is_flag=True, default=False, help="Only show pinned notes."
)
@click.option(
    "--output",
    type=click.Path(exists=False, writable=True, file_okay=True, dir_okay=False),
    default=Path("out.md"),
    help="Output file",
)
@click.option("--show", is_flag=True, default=False, help="Show markdown.")
@main.command()
@click.pass_obj
def md(cfg: Config, structure: Path, only_pinned: bool, output: Path, show: bool) -> None:
    log.trace("Generating markdown")
    history = get_history()
    history = list(filter(lambda x: x.pinned, history)) if only_pinned else history
    click.echo(f"Found {len(history)} notes")
    click.echo("Generating markdown")
    click.echo("Writing markdown")
    md = generate_markdown(cfg, structure, history)
    click.echo("Done.")
    output.write_text(md)
    if show:
        click.echo(" start ".center(70, "-"))
        click.echo(md)
        click.echo("  end  ".center(70, "-"))


@click.option(
    "--structure",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
    default=STRUCTURE_PATH,
)
@click.option(
    "--only-pinned", is_flag=True, default=False, help="Only show pinned notes."
)
@click.option(
    "--output",
    type=click.Path(exists=False, writable=True, file_okay=True, dir_okay=False),
    default=Path("out.md"),
    help="Output file",
)
@click.option("--show", is_flag=True, default=False, help="Show markdown.")
@click.option("--reference-id", default=REFERENCE_ID, help="Reference ID to update.")
@main.command()
@click.pass_obj
def upload_reference(
    cfg: Config,
    structure: Path,
    only_pinned: bool,
    output: Path,
    show: bool,
    reference_id: str,
) -> None:
    click.echo("(- uploading reference -)")
    history = get_history()
    history = list(filter(lambda x: x.pinned, history)) if only_pinned else history
    click.echo(f"Found {len(history)} notes")
    click.echo("Generating markdown")
    click.echo("Writing markdown")
    md = generate_markdown(cfg, structure, history)
    output.write_text(md)
    if show:
        click.echo(" start ".center(70, "-"))
        click.echo(md)
        click.echo("  end  ".center(70, "-"))

    click.echo(f"Uploading to {cfg.server}/{reference_id}")
    upload_md_reference(output, reference_id)


if __name__ == "__main__":
    main()
