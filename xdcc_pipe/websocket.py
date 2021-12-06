import uuid

import fastapi
from fastapi.websockets import WebSocket, WebSocketDisconnect
from websockets import connect as ws_connect
from websockets.exceptions import ConnectionClosedOK

from .irc import IrcBot
from .model import Pack


class XDCCPipe:
    app = fastapi.FastAPI()

    @app.websocket("/{client_id}")
    async def forward_pack(websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        try:
            pack = Pack(**await websocket.receive_json())

            await IrcBot().forward(pack, websocket)
            await websocket.close()
        except WebSocketDisconnect:
            print(f"Client #{client_id} has disconnected.")

    @staticmethod
    async def request_pack(ws_url: str, pack: Pack, target_file: str) -> None:
        client_id = uuid.uuid4()

        async with ws_connect(f"{ws_url}/{client_id}") as websocket:
            try:
                await websocket.send(pack.json())

                with open(target_file, "wb") as fp:
                    while True:
                        chunk = await websocket.recv()
                        fp.write(chunk)

                await websocket.close()
            except ConnectionClosedOK:
                pass
