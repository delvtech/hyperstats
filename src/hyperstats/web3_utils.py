import logging
import os
import time
import traceback
import re

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# pylint: disable=redefined-builtin

def create_w3(network):
    w3 = Web3(Web3.HTTPProvider(f"https://{'eth' if network == 'mainnet' else network}-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}"))
    if network == "linea":
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def parse_suggested_block_range(error_message):
    """Extract suggested block range from RPC error message."""
    match = re.search(r'\[0x([a-f0-9]+), 0x([a-f0-9]+)\]', error_message)
    if match:
        start_block = int(match.group(1), 16)
        end_block = int(match.group(2), 16)
        return start_block, end_block
    return None, None


def fetch_events_logs_with_retry(
    contract_event,
    from_block: int,
    to_block: int | str = "latest",
    retries: int = 3,
    delay: int = 2,
    label: str | None = None,
    filter: dict | None = None,
) -> list:
    """Fetch event logs with retry logic and handling of block range limits."""
    if isinstance(to_block, str) and to_block == "latest":
        to_block = contract_event.w3.eth.block_number

    current_from_block = from_block
    all_logs = []

    while current_from_block <= to_block:
        for attempt in range(retries):
            try:
                logs = contract_event.get_logs(
                    from_block=current_from_block,
                    to_block=to_block if filter is None else None,
                    argument_filters=filter
                )
                all_logs.extend(logs)
                return all_logs
            except Exception as e:
                if "Log response size exceeded" in str(e):
                    suggested_start, suggested_end = parse_suggested_block_range(str(e))
                    if suggested_start and suggested_end:
                        # Use suggested range for next iteration
                        print(f"log response size exceeded\n => re-querying with {suggested_start=}, {suggested_end=}")
                        logs = contract_event.get_logs(
                            from_block=current_from_block,
                            to_block=suggested_end,
                            argument_filters=filter
                        )
                        all_logs.extend(logs)
                        current_from_block = suggested_end + 1
                        break
                    else:
                        # If can't parse suggested range, use a smaller fixed range
                        next_block = min(current_from_block + 2000, to_block)
                        print(f"log response size exceeded\n => re-querying with {current_from_block=}, {next_block=}")
                        logs = contract_event.get_logs(
                            from_block=current_from_block,
                            to_block=next_block,
                            argument_filters=filter
                        )
                        all_logs.extend(logs)
                        current_from_block = next_block + 1
                        break
                elif attempt < retries - 1:
                    time.sleep(delay)
                    continue
                else:
                    msg = (
                        f"Error getting events logs"
                        f" for {label}" if label is not None else ""
                        f": {e}, {traceback.format_exc()}"
                    )
                    logging.error(msg)
                    raise e

    return all_logs
