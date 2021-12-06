import asyncio
import random
import ssl
import struct

import fastapi
import irc3

from .model import Pack


class XDCCGet(irc3.dcc.client.DCCGet):
    def connection_made(self, transport) -> None:
        super(irc3.dcc.client.DCCGet, self).connection_made(transport)
        if self.resume:
            self.bytes_received = self.offset
        else:
            self.bytes_received = 0

    def data_received(self, data) -> None:
        self.set_timeout()

        task = self.bot.loop.create_task(self.bot.websocket.send_bytes(data))
        task.add_done_callback(lambda t: t.result())

        self.bytes_received += len(data)
        self.transport.write(struct.pack("!Q", self.bytes_received))

    @classmethod
    async def initiate(cls, bot, mask, filesize, host, port):
        return bot.dcc.create(
            cls, mask, filepath=True, filesize=filesize, host=host, port=port
        )


@irc3.plugin
class IrcBot:
    def __init__(self, context=None) -> None:
        self.context = context

        self.cfg = dict(
            port=6697,
            ssl=True,
            ssl_verify=ssl.CERT_NONE,
            includes=["irc3.plugins.core", __name__],
            client_id="Irssi 0.8.19 (20160323) - http://irssi.org/",
            verbose=True,
            raw=False,
            loop=asyncio.get_event_loop(),
        )

        nick = "AcMe" + str(hex(random.randrange(0x1337)))[2:]
        for k in ("nick", "username", "realname"):
            self.cfg[k] = nick

    @irc3.event(irc3.rfc.CONNECTED)
    def connected(self, **_: int) -> None:
        self.context.log.info("bot connected")

        required_channels = self.context.requested_pack.channels
        self.context.log.info(f"joining: {required_channels}")
        for channel in self.context.requested_pack.channels:
            self.context.join(channel)

        # Backoff for a minute, since some peers require this.
        self.context.loop.call_later(60, self.request_pack)

    def request_pack(self) -> None:
        pack = self.context.requested_pack
        self.context.privmsg(pack.peer, f"XDCC SEND {pack.number}")
        self.context.log.info("pack has been requested")

    @irc3.event(irc3.rfc.CTCP)
    async def on_ctcp(self, mask, **kwargs) -> None:
        if kwargs["ctcp"] == "VERSION":
            self.context.send_line("VERSION " + self.context.config.client_id)
            return

        name, host, port, size, *_ = kwargs["ctcp"].split()[2:]
        self.context.log.info("%s is offering %s", mask.nick, name)

        conn = await self.context.create_task(
            XDCCGet.initiate(self.context, mask, int(size), host, port)
        )
        await conn.closed

        self.context.file_received.set_result(True)
        self.context.log.info("file received from %s", mask.nick)

    async def forward(self, pack: Pack, websocket: fastapi.WebSocket) -> None:
        self.receiver = irc3.IrcBot.from_config(self.cfg, host=pack.network)
        self.receiver.requested_pack = pack
        self.receiver.websocket = websocket
        self.receiver.file_received = asyncio.Future()
        self.receiver.run(forever=False)
        await self.receiver.file_received
        self.disconnect()

    def disconnect(self) -> None:
        self.receiver.registry.plugins["irc3.plugins.core.Core"].reconn_handle.cancel()
        self.receiver.registry.plugins["irc3.plugins.core.Core"].ping_handle.cancel()
        self.receiver.protocol.connection_lost = lambda _: _
        self.receiver.protocol.transport.close()
        self.receiver.awaiting_queue.cancel()
        del self.receiver
