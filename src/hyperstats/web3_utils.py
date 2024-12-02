import logging
import os
import time
import traceback

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


def create_w3(network):
    w3 = Web3(Web3.HTTPProvider(f"https://{'eth' if network == 'mainnet' else network}-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}"))
    if network == "linea":
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def fetch_events_logs_with_retry(
    label: str,
    contract_event,
    from_block: int,
    to_block: int | str = "latest",
    retries: int = 3,
    delay: int = 2,
    filter: dict | None = None,
) -> dict | None:
    for attempt in range(retries):
        try:
            if filter is None:
                return contract_event.get_logs(from_block=from_block, to_block=to_block)
            else:
                return contract_event.get_logs(filter)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            else:
                msg = f"Error getting events logs for {label}: {e}, {traceback.format_exc()}"
                logging.error(msg)
                raise e
