import aio_pika
import asyncio
import logging
from config import rabbitmq_url


async def connect_to_rabbitmq():
    retries = 5
    for attempt in range(retries):
        try:
            connection = await aio_pika.connect_robust(rabbitmq_url)
            logging.info("Successfully connected to RabbitMQ.")
            return connection
        except Exception as e:
            logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(5)  # Wait before retrying

    raise Exception("Failed to connect to RabbitMQ after several attempts.")
