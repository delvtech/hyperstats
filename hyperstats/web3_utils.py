import logging
import time
import traceback

from web3 import Web3

from hyperstats.constants import ETH_NODE_URL

# pylint: disable=redefined-builtin

# defaults to http://localhost:8545 if you don't set ETH_NODE_URL
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

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
                return contract_event.get_logs(fromBlock=from_block, toBlock=to_block)
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
