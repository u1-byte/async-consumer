import os

consumer_count = int(os.getenv("CONSUMER_COUNT", "15"))
rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
rabbitmq_queue = os.getenv("RABBITMQ_QUEUE", "base_queue")
rabbitmq_dlq = os.getenv("RABBITMQ_DLQ", "err_queue")
rabbitmq_max_retry = int(os.getenv("RABBITMQ_MAX_RETRY", "5"))
