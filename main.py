import argparse
import asyncio
import logging
from src.consumer import main as main_consumer
from src.producer import produce_data as main_producer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["consumer", "producer"])
    args = parser.parse_args()
    if args.command == "consumer":
        asyncio.run(main_consumer())
    elif args.command == "producer":
        asyncio.run(main_producer())


if __name__ == "__main__":
    main()
