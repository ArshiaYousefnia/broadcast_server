from asyncio import start_server, StreamReader, StreamWriter
import logging

logger = logging.getLogger(__name__)

class BroadcastServer:
    def __init__(self, port: int=5000, host: str="0.0.0.0"):
        self.host = host
        self.port = port
        self.connections = set()
        self.server = None

    async def start_server(self):
        self.server = await start_server(
            self._handle_connection,
            host=self.host,
            port=self.port,
        )

        logger.info("server started")

        async with self.server:
            await self.server.serve_forever()

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter):
        address = writer.get_extra_info("peername")
        self.connections.add(writer)
        logger.info(f"new connection from {address}")

        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                message = data.decode()
                logger.info(f"Received {message} from {address}")

                await self._broadcast_message(message)
        except ConnectionError:
            logger.info(f"{address} disconnected")
        finally:
            self.connections.discard(writer)
            writer.close()
            await writer.wait_closed()
            logger.info(f"{address} connection closed")

    async def _broadcast_message(self, message: str):
        for writer in list(self.connections):
            try:
                writer.write(message.encode('utf-8'))
                await writer.drain()
            except ConnectionError:
                self.connections.discard(writer)
                logger.info(f"Connection to {writer} closed")
                writer.close()




