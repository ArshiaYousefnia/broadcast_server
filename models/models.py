import asyncio
import sys
from asyncio import start_server, StreamReader, StreamWriter
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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


class BroadcastClient:
    def __init__(self, port=5000, host="0.0.0.0"):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def run(self):
        await self._connect_to_server()

        receiver_task = asyncio.create_task(self._receive_message())
        sender_task = asyncio.create_task(self._send_message())

        try:
            await asyncio.gather(receiver_task, sender_task)
        except asyncio.CancelledError:
            pass
        finally:
            if self.writer and not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
            logger.info("client disconnected")

    async def _connect_to_server(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        logger.info(f"connected to server at {self.host}:{self.port}")

    async def _send_message(self):
        loop = asyncio.get_event_loop()

        while True:
            try:
                message = await loop.run_in_executor(None, input, ">")
                message = message.strip()
                if not message:
                    continue
                if message.lower() == 'exit':
                    break
                self.writer.write(message.encode('utf-8'))
                await self.writer.drain()
            except Exception as e:
                logger.error(f"unexpected error: {e}")
                break
        self.writer.close()
        await self.writer.wait_closed()

    async def _receive_message(self):
        try:
            while True:
                data = await self.reader.read(1024)
                if not data:
                    logger.info("server closed connection")
                    break
                message = data.decode()
                print(f"\nreceived: {message}")
        except ConnectionResetError:
            logger.error("connection reset by server")
        finally:
            self.writer.close()
            await self.writer.wait_closed()





