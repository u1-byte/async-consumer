import aio_pika
import json
import logging
from config import rabbitmq_queue
from src.rabbitmq_connection import connect_to_rabbitmq

data = [
    {"id": i, "name": f"message{i}", "description": f"This is dummy message {i}"}
    for i in range(1, 501)
]


async def produce_data():
    connection = await connect_to_rabbitmq()
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(rabbitmq_queue, durable=True)
        for item in data:
            message = json.dumps(item)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=rabbitmq_queue,
            )
            logging.info(f"Sent: {message}")
