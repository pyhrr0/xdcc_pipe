import argparse
import asyncio
import logging
import urllib.parse

import uvicorn

from .model import Pack
from .websocket import XDCCPipe


def _parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["server", "client"], help="mode")
    parser.add_argument("-f", "--output-file", default="/dev/stdout", type=str)
    parser.add_argument("-n", "--network", type=str, help="network to connect to")
    parser.add_argument(
        "-c", "--channels", type=str, help="comma separated list of channel(s) to join"
    )
    parser.add_argument("-b", "--bot", type=str, help="bot to request pack from")
    parser.add_argument("-p", "--pack_num", type=int, help="pack number to request")
    parser.add_argument(
        "-u",
        "--ws-url",
        default="ws://localhost:1234",
        type=str,
        help="address to serve on / connect to",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")

    args = parser.parse_args()
    if args.mode == "client":
        required = ("network", "channels", "bot", "pack_num")
        if any(not getattr(args, arg) for arg in required):
            parser.print_usage()
            exit(1)

    return parser.parse_args()


def main() -> None:
    cli_args = _parse_cli_args()

    level = logging.INFO
    if cli_args.verbose:
        level = logging.DEBUG

    logging.basicConfig(format="[%(asctime)s] %(levelname)-8s %(message)s", level=level)

    if cli_args.mode == "client":
        asyncio.run(
            XDCCPipe.request_pack(
                cli_args.ws_url, Pack.from_args(cli_args), cli_args.output_file
            )
        )
    else:
        url = urllib.parse.urlparse(cli_args.ws_url)
        uvicorn.run(XDCCPipe.app, host=url.hostname, port=url.port)


if __name__ == "__main__":
    main()
