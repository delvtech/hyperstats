import logging
import os
import re
import time
import traceback

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# pylint: disable=redefined-builtin

# Chain configurations for Base networks
CHAIN_CONFIGURATIONS = {
    "mainnet": {
        "chain_id": 8453,
        "network_name": "Base Mainnet",
        "bns_address": "0xeCBaE6E54bAA669005b93342E5650d5886D54fc7",
    },
    "testnet": {
        "chain_id": 84531,
        "network_name": "Base Goerli Testnet",
        "bns_address": "0xAFCc9Ba1ac174CB5347c07FaeddE8BF8b4aBa40a",
    },
    "linea": {
        "chain_id": 84531,
        "network_name": "Linea Testnet",
        "bns_address": "0xAFCc9Ba1ac174CB5347c07FaeddE8BF8b4aBa40a",
    },
}

# BNS Constants
REVERSE_REGISTRAR_ADDRESS = "0x79ea96012eea67a83431f1701b3dff7e37f9e282"
L2_RESOLVER_ADDRESS = "0xC6d566A56A1aFf6508b41f6c90ff131615583bcd"

REVERSE_REGISTRAR_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "addr", "type": "address"}],
        "name": "node",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "pure",
        "type": "function"
    }
]

RESOLVER_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "node", "type": "bytes32"}],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def get_bns_name(provider: Web3, address: str) -> str:
    """Look up the BNS name associated with a given address.

    Args:
        provider: Web3 provider instance
        address: Ethereum address to look up

    Returns:
        str: Resolved BNS name or empty string if not found
    """
    try:
        # Convert address to checksum format
        address = provider.to_checksum_address(address)

        # Create contract instances
        reverse_registrar = provider.eth.contract(
            address=provider.to_checksum_address(REVERSE_REGISTRAR_ADDRESS),
            abi=REVERSE_REGISTRAR_ABI
        )
        resolver = provider.eth.contract(
            address=provider.to_checksum_address(L2_RESOLVER_ADDRESS),
            abi=RESOLVER_ABI
        )

        # Get node from reverse registrar
        node = reverse_registrar.functions.node(address).call()

        # Get name from resolver
        name = resolver.functions.name(node).call()
        return name

    except Exception as error:
        print(f"Error in BNS lookup: {error}")
        return ""

def get_namehash(name: str) -> bytes:
    """Calculate the namehash for a domain name."""
    if not name:
        return b'\0' * 32

    # For reverse address lookup
    if name.endswith('.addr.reverse'):
        # Special handling for reverse lookup
        labels = name.split('.')

        # The address part needs to be split into individual characters
        addr_chars = list(labels[0])  # Split address into individual characters
        labels = addr_chars + labels[1:]  # Add back 'addr' and 'reverse'
    else:
        # Remove .eth suffix if present
        if name.endswith('.eth'):
            name = name[:-4]
        # Remove .base suffix if present
        if name.endswith('.base'):
            name = name[:-5]
        # Add .base.eth for resolution
        name = name + '.base.eth'
        labels = name.split('.')

    node = b'\0' * 32
    for label in reversed(labels):
        label_hash = Web3.keccak(text=label)
        node = Web3.keccak(node + label_hash)
    return node

def get_address(provider: Web3, name: str) -> str:
    """Resolve the address associated with a given BNS name.

    Args:
        provider: Web3 provider instance
        name: BNS name to resolve

    Returns:
        str: Resolved address or empty string if not found
    """
    try:
        # Calculate namehash
        node = get_namehash(name)

        # Create contract instance
        resolver = provider.eth.contract(
            address=provider.to_checksum_address(L2_RESOLVER_ADDRESS),
            abi=RESOLVER_ABI
        )
        # Get address directly from resolver
        address = resolver.functions.addr(node).call()
        if address:
            return provider.to_checksum_address(address)
        return ""

    except Exception as error:
        print(f"Error resolving address for {name}: {error}")
        return ""

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
