#!/usr/bin/env python
"""Track and analyze Hyperdrive protocol trading events.

This script tracks specific trading events (AddLiquidity, RemoveLiquidity, OpenLong, 
CloseLong, OpenShort, CloseShort) and stores them in a Parquet file for analysis.
"""
import argparse
import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
from web3 import Web3

from hyperstats.constants import HYPERDRIVE_MORPHO_ABI, HYPERDRIVE_REGISTRY
from hyperstats.utils import get_first_contract_block, get_instance_list
from hyperstats.web3_utils import create_w3, fetch_events_logs_with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Event types we're tracking
EVENT_TYPES = [
    "AddLiquidity",
    "RemoveLiquidity", 
    "OpenLong", 
    "CloseLong", 
    "OpenShort", 
    "CloseShort"
]

# Parquet file path
EVENTS_FILE = "hyperdrive_events.parquet"

def process_event(event: Dict, network: str, pool_address: str, pool_name: str) -> Dict:
    """Process an event log into a standardized format."""
    # Start with the event args
    result = dict(event["args"])
    
    # Add common metadata
    result["network"] = network
    result["pool_address"] = pool_address
    result["pool_name"] = pool_name
    result["block_number"] = event["blockNumber"]
    result["block_timestamp"] = event["timestamp"] if "timestamp" in event else 0
    result["transaction_hash"] = event["transactionHash"].hex()
    result["log_index"] = event["logIndex"]
    result["event_type"] = event["event"]
    
    # Special handling for specific fields
    if event["event"] in ["AddLiquidity", "RemoveLiquidity"] and "provider" in result:
        # Rename provider to trader for consistency
        result["trader"] = result["provider"]
    
    # Convert all numeric values to strings to avoid precision issues
    for key, value in list(result.items()):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = str(value)
    
    return result

def fetch_events(
    w3: Web3,
    contract,
    event_name: str,
    from_block: int,
    to_block: int,
) -> List[Dict]:
    """Fetch events of a specific type from the blockchain."""
    event_obj = getattr(contract.events, event_name)

    logs = fetch_events_logs_with_retry(
        contract_event=event_obj(),
        from_block=from_block,
        to_block=to_block,
        label=f"{event_name} events",
    )

    # Add block timestamps
    for i, log in enumerate(logs):
        # Convert AttributeDict to dict to allow modification
        log_dict = dict(log)
        if "timestamp" not in log_dict:
            block = w3.eth.get_block(log_dict["blockNumber"])
            log_dict["timestamp"] = block.timestamp
        logs[i] = log_dict

    return logs

def track_pool_events(
    network: str,
    pool_address: str,
    from_block: int = None,
    to_block: int = None,
    pool_name: str = None,
) -> pd.DataFrame:
    """Track events for a specific pool and return as DataFrame."""
    w3 = create_w3(network)

    # Normalize address
    pool_address = Web3.to_checksum_address(pool_address)

    # Get pool name if not provided
    if pool_name is None:
        pool_name = "%s:%s" % (network, pool_address)

    # Create contract instance
    contract = w3.eth.contract(address=pool_address, abi=HYPERDRIVE_MORPHO_ABI)

    # If from_block not specified, get deployment block
    if from_block is None:
        deployment_block, _ = get_first_contract_block(w3, pool_address)
        from_block = deployment_block

    # Get latest block if to_block not specified
    if to_block is None:
        to_block = w3.eth.block_number

    logging.info("Fetching events for pool %s on %s from block %s to %s", 
                pool_address, network, from_block, to_block)

    all_events = []

    # Fetch and process each event type
    for event_type in EVENT_TYPES:
        logging.info("Fetching %s events...", event_type)

        # Fetch events
        events = fetch_events(w3, contract, event_type, from_block, to_block)

        if not events:
            logging.info("No %s events found", event_type)
            continue

        logging.info("Found %d %s events", len(events), event_type)

        # Process events
        processed_events = [
            process_event(event, network, pool_address, pool_name)
            for event in events
        ]

        all_events.extend(processed_events)

    # Convert to DataFrame
    if not all_events:
        return pd.DataFrame()

    return pd.DataFrame(all_events)

def track_network_events(network: str, from_block: int = None, to_block: int = None) -> pd.DataFrame:
    """Track events for all pools in a network and return as DataFrame."""
    # Use the existing get_instance_list function to get pools
    w3, pool_addresses = get_instance_list(network)
    
    # Convert pool addresses to (address, name) tuples
    pools = [(address, f"{network}:{address}") for address in pool_addresses]
    
    logging.info("Found %d pools on %s", len(pools), network)

    # Track events for each pool
    all_dfs = []
    for pool_address, pool_name in pools:
        df = track_pool_events(network, pool_address, from_block, to_block, pool_name)
        if not df.empty:
            all_dfs.append(df)

    # Combine all DataFrames
    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)

def save_events(df: pd.DataFrame, file_path: str = EVENTS_FILE) -> None:
    """Save events to a Parquet file, appending to existing data if present."""
    if df.empty:
        logging.info("No events to save")
        return

    try:
        # Try to read existing file
        existing_df = pd.read_parquet(file_path)

        # Combine with new data
        combined_df = pd.concat([existing_df, df], ignore_index=True)

        # Remove duplicates based on transaction hash and log index
        combined_df = combined_df.drop_duplicates(
            subset=['network', 'transaction_hash', 'log_index'], 
            keep='last'
        )

        # Sort by block number
        combined_df = combined_df.sort_values(['block_number', 'log_index'])

        # Save to file
        combined_df.to_parquet(file_path, index=False)
        logging.info("Saved %d new events to %s, total: %d", 
                    len(df), file_path, len(combined_df))

    except (FileNotFoundError, OSError):
        # File doesn't exist, create new
        df.to_parquet(file_path, index=False)
        logging.info("Created new file %s with %d events", file_path, len(df))

def load_events(file_path: str = EVENTS_FILE) -> pd.DataFrame:
    """Load events from a Parquet file."""
    try:
        return pd.read_parquet(file_path)
    except (FileNotFoundError, OSError):
        logging.warning("Events file %s not found", file_path)
        return pd.DataFrame()

def analyze_pool(network: str, pool_address: str):
    """Analyze events for a specific pool."""
    # Load all events
    df = load_events()

    if df.empty:
        logging.error("No events found")
        return

    # Filter for the specific pool
    df = df[(df['network'] == network) & (df['pool_address'] == pool_address)]

    if df.empty:
        logging.error("No events found for pool %s on %s", pool_address, network)
        return

    # Convert timestamp to datetime for better display
    # Explicitly convert to numeric to avoid FutureWarning
    df['datetime'] = pd.to_datetime(pd.to_numeric(df['block_timestamp']), unit='s')

    # Sort by block number and timestamp
    df = df.sort_values(['block_number', 'log_index'])

    # Print basic statistics
    print("\n=== Pool Analysis: %s on %s ===" % (pool_address, network))
    print("Total events: %d" % len(df))
    print("Date range: %s to %s" % (df['datetime'].min(), df['datetime'].max()))

    # Count by event type
    event_counts = df['event_type'].value_counts()
    print("\nEvent counts:")
    for event_type, count in event_counts.items():
        print("  %s: %d" % (event_type, count))

    # Unique traders
    if 'trader' in df.columns:
        unique_traders = df['trader'].nunique()
        print("\nUnique traders: %d" % unique_traders)

        # Top traders by event count
        top_traders = df['trader'].value_counts().head(10)
        print("\nTop 10 traders by event count:")
        for trader, count in top_traders.items():
            print("  %s: %d" % (trader, count))

    # Event volume over time (weekly)
    df['week'] = df['datetime'].dt.isocalendar().week
    df['year'] = df['datetime'].dt.isocalendar().year
    df['year_week'] = df['year'].astype(str) + '-' + df['week'].astype(str)

    weekly_events = df.groupby(['year_week', 'event_type']).size().unstack(fill_value=0)

    # Save to CSV
    output_dir = Path("analysis") / network
    output_dir.mkdir(exist_ok=True, parents=True)

    weekly_events.to_csv(output_dir / f"{pool_address}_weekly_events.csv")
    df.to_csv(output_dir / f"{pool_address}_all_events.csv", index=False)

    print(f"\nAnalysis saved to analysis/{network}/{pool_address}_*.csv")

def analyze_trader(network: str, trader_address: str):
    """Analyze events for a specific trader across all pools."""
    # Load all events
    df = load_events()

    if df.empty:
        logging.error("No events found")
        return

    # Filter for the specific network and trader
    if 'trader' not in df.columns:
        logging.error("No trader field found in events data")
        return

    df = df[(df['network'] == network) & (df['trader'] == trader_address)]

    if df.empty:
        logging.error("No events found for trader %s on %s", trader_address, network)
        return

    # Convert timestamp to datetime for better display
    # Explicitly convert to numeric to avoid FutureWarning
    df['datetime'] = pd.to_datetime(pd.to_numeric(df['block_timestamp']), unit='s')

    # Sort by block number and timestamp
    df = df.sort_values(['block_number', 'log_index'])

    # Print basic statistics
    print("\n=== Trader Analysis: %s on %s ===" % (trader_address, network))
    print("Total events: %d" % len(df))
    print("Date range: %s to %s" % (df['datetime'].min(), df['datetime'].max()))

    # Count by event type
    event_counts = df['event_type'].value_counts()
    print("\nEvent counts:")
    for event_type, count in event_counts.items():
        print("  %s: %d" % (event_type, count))

    # Count by pool
    pool_counts = df['pool_address'].value_counts()
    print("\nPool activity:")
    for pool, count in pool_counts.items():
        print("  %s: %d" % (pool, count))

    # Save to CSV
    output_dir = Path("analysis") / network
    output_dir.mkdir(exist_ok=True, parents=True)

    df.to_csv(output_dir / f"trader_{trader_address}.csv", index=False)

    print(f"\nAnalysis saved to analysis/{network}/trader_{trader_address}.csv")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Track and analyze Hyperdrive protocol trading events")

    # Main command options
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Track events for a specific network
    network_parser = subparsers.add_parser("track-network", help="Track events for all pools in a network")
    network_parser.add_argument(
        "network", 
        choices=HYPERDRIVE_REGISTRY.keys(),
        help="Network to track events for"
    )
    network_parser.add_argument(
        "--from-block", 
        type=int, 
        help="Block number to start tracking from (default: deployment block)"
    )
    network_parser.add_argument(
        "--to-block", 
        type=int, 
        help="Block number to track events up to (default: latest)"
    )

    # Track events for a specific pool
    pool_parser = subparsers.add_parser("track-pool", help="Track events for a specific pool")
    pool_parser.add_argument(
        "network", 
        choices=HYPERDRIVE_REGISTRY.keys(),
        help="Network the pool is on"
    )
    pool_parser.add_argument(
        "pool_address", 
        help="Address of the pool to track events for"
    )
    pool_parser.add_argument(
        "--from-block", 
        type=int, 
        help="Block number to start tracking from (default: deployment block)"
    )
    pool_parser.add_argument(
        "--to-block", 
        type=int, 
        help="Block number to track events up to (default: latest)"
    )

    # Track events for all networks
    all_parser = subparsers.add_parser("track-all", help="Track events for all networks")
    all_parser.add_argument(
        "--from-block", 
        type=int, 
        help="Block number to start tracking from (default: deployment block)"
    )
    all_parser.add_argument(
        "--to-block", 
        type=int, 
        help="Block number to track events up to (default: latest)"
    )

    # Analyze a specific pool
    analyze_pool_parser = subparsers.add_parser("analyze-pool", help="Analyze events for a specific pool")
    analyze_pool_parser.add_argument(
        "network", 
        choices=HYPERDRIVE_REGISTRY.keys(),
        help="Network the pool is on"
    )
    analyze_pool_parser.add_argument(
        "pool_address", 
        help="Address of the pool to analyze"
    )

    # Analyze a specific trader
    analyze_trader_parser = subparsers.add_parser("analyze-trader", help="Analyze events for a specific trader")
    analyze_trader_parser.add_argument(
        "network", 
        choices=HYPERDRIVE_REGISTRY.keys(),
        help="Network to analyze"
    )
    analyze_trader_parser.add_argument(
        "trader_address", 
        help="Address of the trader to analyze"
    )

    return parser.parse_args()

def main():
    """Run the main command processing logic."""
    args = parse_args()

    # Create analysis directory if it doesn't exist
    Path("analysis").mkdir(exist_ok=True)

    if args.command == "track-network":
        df = track_network_events(args.network, args.from_block, args.to_block)
        save_events(df)
    elif args.command == "track-pool":
        df = track_pool_events(args.network, args.pool_address, args.from_block, args.to_block)
        save_events(df)
    elif args.command == "track-all":
        all_dfs = []
        for network in HYPERDRIVE_REGISTRY.keys():
            df = track_network_events(network, args.from_block, args.to_block)
            all_dfs.append(df)
        if all_dfs:
            save_events(pd.concat(all_dfs, ignore_index=True))
    elif args.command == "analyze-pool":
        analyze_pool(args.network, args.pool_address)
    elif args.command == "analyze-trader":
        analyze_trader(args.network, args.trader_address)
    else:
        logging.error("No command specified. Use --help for usage information.")

if __name__ == "__main__":
    main()
