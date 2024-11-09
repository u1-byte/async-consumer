import json
import asyncio
import aio_pika
import time
import random
from datetime import timedelta, datetime
import time
import logging

from config import rabbitmq_queue, rabbitmq_dlq, rabbitmq_max_retry, consumer_count
from src.rabbitmq_connection import connect_to_rabbitmq

unacked_count = 0
processed_count = 0


def get_time_sleep():
    return random.randint(10, 20)


def get_error_state():
    return random.choice([True, False])


def main_running(data, on_complete):
    try:
        # Randomly simulate exception thrown
        if get_error_state():
            raise ValueError("Something went wrong.")
        # Randomly simulate time to process
        time.sleep(get_time_sleep())
        logging.info(f"Processed data: {data}")
    except Exception as e:
        raise e
    finally:
        on_complete()


async def post_process_observer():
    global processed_count
    interval = timedelta(minutes=5).total_seconds()
    while True:
        if unacked_count == 0 and processed_count > 0:
            finish_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"Finish at: {finish_date}")
            processed_count = 0
        await asyncio.sleep(interval)  # Trigger check completeness every 5 minutes


async def requeue_message(
    message: aio_pika.IncomingMessage, channel: aio_pika.Channel, retry_count: int
):
    headers = message.headers or {}
    headers["retry_count"] = retry_count  # Update retry count in headers

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=message.body,
            headers=headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=message.routing_key,  # Send back to the original queue
    )


async def send_to_err_queue(
    message: aio_pika.IncomingMessage, channel: aio_pika.Channel
):
    # Publish the message to the dead letter queue
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=message.body,
            headers=message.headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=rabbitmq_dlq,
    )


async def process_message(
    message: aio_pika.IncomingMessage,
    semaphore: asyncio.Semaphore,
    channel: aio_pika.Channel,
):
    global unacked_count
    unacked_count += 1
    async with semaphore:  # Limit concurrent processing
        async with message.process():  # This acknowledges the message on success
            data = json.loads(message.body)
            # Get the current retry count from message headers (default to 0)
            retry_count = int(message.headers.get("retry_count", 0))

            # Callback function to update unacked and processed count
            def complete_callback():
                global processed_count, unacked_count
                processed_count += 1
                unacked_count -= 1

            try:
                # Run sync function
                await asyncio.to_thread(main_running, data, complete_callback)
            except Exception as e:
                logging.error(f"Exception - {data}: {e}")
                # Check if the retry count has exceeded the max retries
                if retry_count >= int(rabbitmq_max_retry):
                    # Publish the message to dead letter queue
                    await send_to_err_queue(message, channel)
                    logging.warning(f"Sent to DLQ: {data}")
                else:
                    # Requeue the message with an updated retry count
                    retry_count = retry_count + 1
                    await requeue_message(message, channel, retry_count)
                    logging.warning(f"Requeue for {retry_count} times: {data}")


async def main():
    # Create a semaphore to limit async worker
    semaphore = asyncio.Semaphore(consumer_count)
    connection = await connect_to_rabbitmq()
    async with connection:
        channel = await connection.channel()

        # Set QOS
        await channel.set_qos(prefetch_count=consumer_count * 2)

        # Declare base queue and DLQ
        queue = await channel.declare_queue(rabbitmq_queue, durable=True)
        await channel.declare_queue(rabbitmq_dlq, durable=True)

        # Monitor and trigger postprocess
        asyncio.create_task(post_process_observer())

        # Consume messages asynchronously
        await queue.consume(
            lambda message: process_message(message, semaphore, channel)
        )
        await asyncio.Future()  # Keep the coroutine running
