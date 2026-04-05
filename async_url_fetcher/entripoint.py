import logging
from typing import Literal
from urllib.parse import urlparse

import click
import uvloop
from click.core import Argument, Context

from async_url_fetcher.client.client import main, Seconds
from async_url_fetcher.constants import AVAILABLE_LOG_LEVELS


# Free fake and reliable API for testing and prototyping:
# https://jsonplaceholder.typicode.com/posts

def validate_url(_ctx: Context, _param: Argument, value):
    processed_urls = []
    for url in value:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise click.BadParameter(f"'{url}' is not a valid URL.")
        processed_urls.append(url)
    return processed_urls


@click.command()
@click.argument("urls", nargs=-1, required=True, callback=validate_url)
@click.option("-t", "--timeout", default=5, help="Timeout in seconds")
@click.option("--as_text", default=False, is_flag=True, help="Output as JSON")
@click.option("--log-level", default="INFO",
              type=click.Choice(AVAILABLE_LOG_LEVELS),
              help="Set logging level")
def run(
        urls: list[str],
        as_text: bool,
        timeout: int,
        log_level: Literal[*AVAILABLE_LOG_LEVELS],
) -> None:
    logging.basicConfig(level=log_level)

    click.echo(f"Starting to fetch {len(urls)} URLs")
    uvloop.run(
        main(urls, as_text=as_text, timeout=Seconds(timeout)),
        debug=True
    )
    click.echo(f"Done")


if __name__ == '__main__':
    run()
