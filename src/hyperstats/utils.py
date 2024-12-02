import itertools
import json
import os
import time
from decimal import Decimal, getcontext

import eth_abi
from hexbytes import HexBytes

from hyperstats.constants import (
    ERC20_ABI,
    HYPERDRIVE_FACTORY_ABI,
    HYPERDRIVE_MORPHO_ABI,
    HYPERDRIVE_REGISTRY,
    HYPERDRIVE_REGISTRY_ABI,
    MORPHO_ABI,
    PAGE_SIZE,
    HyperdrivePrefix,
)
from hyperstats.web3_utils import (
    create_w3,
    fetch_events_logs_with_retry,
)

getcontext().prec = 100  # Set precision for Decimal calculations

def get_first_contract_block(w3, contract_address):
    """Find the first block where a contract's code exists.

    Args:
        w3: Web3 instance
        contract_address: Address of the contract to search for

    Returns:
        tuple: (deployment_block, deployment_transaction)
            - deployment_block: Block number where contract was deployed
            - deployment_transaction: Transaction hash and constructor args
    """
    # do binary search up to latest block
    latest_block = w3.eth.get_block_number()
    earliest_block = 0

    # Keep track of first block where we find code
    first_code_block = None

    while earliest_block <= latest_block:
        mid_block = (earliest_block + latest_block) // 2
        attempt_to_get_code = w3.eth.get_code(account=contract_address,block_identifier=mid_block)

        if len(attempt_to_get_code) <= 2:  # "0x" or empty
            # No code at mid_block, deployment must be after
            earliest_block = mid_block + 1
        else:
            # Found code at mid_block, remember it and look earlier
            first_code_block = mid_block
            latest_block = mid_block - 1

    if first_code_block is None:
        raise ValueError(f"Could not find any block with code for contract {contract_address}")

    # The deployment block is the one we found with code
    deployment_block = first_code_block

    # Now find the deployment transaction
    _, extra_data = get_deployment_transaction(w3, contract_address, deployment_block=deployment_block)

    return deployment_block, extra_data

def get_hyperdrive_participants(w3, pool, cache: bool = False, debug: bool = False):
    target_block = w3.eth.get_block_number()
    all_users = all_ids = start_block = None
    if cache and os.path.exists(f"cache/hyperdrive_users_{pool}.json"):
        with open(f"cache/hyperdrive_users_{pool}.json", "r", encoding="utf-8") as f:
            all_users = set(json.load(f))
    else:
        all_users = set()
    if cache and os.path.exists(f"cache/hyperdrive_ids_{pool}.json"):
        with open(f"cache/hyperdrive_ids_{pool}.json", "r", encoding="utf-8") as f:
            all_ids = set(json.load(f))
    else:
        all_ids = set()
    deployment_block = extra_data = None
    if cache and os.path.exists(f"cache/hyperdrive_latest_block_{pool}.json"):
        with open(f"cache/hyperdrive_latest_block_{pool}.json", "r", encoding="utf-8") as f:
            start_block = json.load(f) + 1
        if start_block >= target_block:
            print(f"Skipping pool {pool} because it's up to date.")
            return all_users, all_ids
    else:
        deployment_block, extra_data = get_first_contract_block(w3, pool)
        start_block = deployment_block + 1
    assert all_users is not None, "error: all_users is None"
    assert all_ids is not None, "error: all_ids is None"
    assert start_block is not None, "error: start_block is None"
    contract = w3.eth.contract(address=pool, abi=HYPERDRIVE_MORPHO_ABI)
    if debug:
        print("Fetching Hyperdrive events..", end="")
        start_time = time.time()
    current_block = start_block
    while current_block < target_block:
        to_block = min(current_block + PAGE_SIZE, target_block)
        transfers = fetch_events_logs_with_retry(
            label=f"Hyperdrive users {pool}",
            contract_event=contract.events.TransferSingle(),
            from_block=current_block,
            to_block=to_block,
            delay=0,
        )
        assert transfers is not None, "error: transfers is None"
        for transfer in transfers:
            all_users.add(transfer["args"]["to"])
            all_ids.add(transfer["args"]["id"])
        current_block = to_block
    if debug:
        print(f". done in {time.time() - start_time:0.2f}s")  # type: ignore
    if cache:
        with open(f"cache/hyperdrive_users_{pool}.json", "w", encoding="utf-8") as f:
            json.dump(list(all_users), f)
        with open(f"cache/hyperdrive_ids_{pool}.json", "w", encoding="utf-8") as f:
            json.dump(list(all_ids), f)
        with open(f"cache/hyperdrive_latest_block_{pool}.json", "w", encoding="utf-8") as f:
            json.dump(target_block, f)

    return all_users, all_ids, deployment_block, extra_data

def get_deployment_transaction(w3, contract_address, deployment_block=None):
    """Find the deployment transaction of a smart contract.

    Args:
        w3: Web3 instance
        contract_address: Address of the deployed contract (can be checksummed or lowercase)
        deployment_block: Optional block number where contract was deployed
        
    Returns:
        tuple: (transaction_hash, constructor_args)
            - transaction_hash: The hash of the deployment transaction
            - constructor_args: The decoded constructor arguments if available
    """
    # First find the block where the contract was deployed
    if deployment_block is None:
        deployment_block = get_first_contract_block(w3, contract_address)
    
    block = w3.eth.get_block(deployment_block, full_transactions=True)
    contract_address = contract_address.lower()
    
    # Look for the transaction that created the contract
    for tx in block.transactions:
        try:
            receipt = w3.eth.get_transaction_receipt(tx.hash)
            # Find deployed event in the logs
            for log in receipt.get('logs', []):
                topic = log.get('topics', [None])[0]
                if topic == HexBytes('0xb25b0f0f93209be08152122f1321f6b0ef559a93a67695fff5fea3e5ed234465'):
                    decoded_event = w3.eth.contract(abi=HYPERDRIVE_FACTORY_ABI).events.Deployed().process_log(log)
                    extra_data = decoded_event['args']['extraData']
                    extra_data_decoded = HexBytes(extra_data)
                    if extra_data_decoded[:12] == HexBytes('0x000000000000000000000000'):
                        extra_data_decoded = HexBytes(extra_data_decoded[12:])
                    return tx.hash, extra_data_decoded
                    
        except Exception as e:
            print(f"Error processing transaction {tx.hash}: {e}")
            continue
    
    raise ValueError(f"Could not find deployment transaction for contract {contract_address} in block {deployment_block}")

def decode_asset_id(asset_id: int) -> tuple[int, int]:
    r"""Decode a transaction asset ID into its constituent parts of an identifier, data, and a timestamp.

    First calculate the prefix mask by left-shifting 1 by 248 bits and subtracting 1 from the result.
    This gives us a bit-mask with 248 bits set to 1 and the rest set to 0.
    Then apply this mask to the input ID using the bitwise-and operator `&` to extract
    the lower 248 bits as the timestamp.
    
    The prefix is a unique asset ID which denotes the following trade types:
        LP = 0
        LONG = 1
        SHORT = 2
        WITHDRAWAL_SHARE = 3

    Arguments:
        asset_id: int
            Encoded ID from a transaction. It is a concatenation, [identifier: 8 bits][timestamp: 248 bits]

    Returns:
        tuple[int, int]
            identifier, timestamp
    """
    prefix_mask = (1 << 248) - 1
    prefix = asset_id >> 248  # shr 248 bits
    timestamp = asset_id & prefix_mask  # apply the prefix mask
    return prefix, timestamp

def get_pool_details(w3, pool_contract, deployment_block: int | None = None, extra_data: str | None = None, debug: bool = False, block_number: int | None = None):
    block_identifier = block_number or "latest"

    # get pool name
    name = pool_contract.functions.name().call()

    # get pool config
    config_values = pool_contract.functions.getPoolConfig().call()
    config_outputs = pool_contract.functions.getPoolConfig().abi['outputs'][0]['components']
    config_keys = [i['name'] for i in config_outputs if 'name' in i]
    config = dict(zip(config_keys, config_values))
    if deployment_block is not None:
        config['deploymentBlock'] = deployment_block
    if extra_data is not None:
        config['extraData'] = extra_data
    if debug:
        print(f"POOL {pool_contract.address[:8]} ({name}) CONFIG:")
        for k,i in config.items():
            print(f" {k:<31} = {i}")

    # get pool info
    info_values = pool_contract.functions.getPoolInfo().call(block_identifier=block_identifier)
    info_outputs = pool_contract.functions.getPoolInfo().abi['outputs'][0]['components']
    info_keys = [i['name'] for i in info_outputs if 'name' in i]
    info = dict(zip(info_keys, info_values))
    if debug:
        print(f"POOL {pool_contract.address[:8]} ({name}) INFO:")
        for k,i in info.items():
            print(f" {k:<31} = {i}")
    lp_short_positions = info['longExposure']

    # query pool holdings of base and vault tokens
    base_token_balance = vault_shares_balance = vault_contract_address = vault_contract = vault_shares_contract = None
    if config["baseToken"] == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
        # the base token is ETH
        base_token_balance = w3.eth.get_balance(pool_contract.address)
    elif " LP " in name:
        base_token_contract = w3.eth.contract(address=config["extraData"], abi=ERC20_ABI)
        base_token_balance = base_token_contract.functions.balanceOf(pool_contract.address).call(block_identifier=block_identifier)
    elif config["baseToken"] != "0x0000000000000000000000000000000000000000":
        base_token_contract = w3.eth.contract(address=config["baseToken"], abi=ERC20_ABI)
        base_token_balance = base_token_contract.functions.balanceOf(pool_contract.address).call(block_identifier=block_identifier)
    if "Morpho" in name:
        vault_contract_address = pool_contract.functions.vault().call(block_identifier=block_identifier)
        vault_contract = w3.eth.contract(address=vault_contract_address, abi=MORPHO_ABI)
        morpho_market_id = w3.keccak(eth_abi.encode(  # type: ignore
            ("address", "address", "address", "address", "uint256"),
            (
                config["baseToken"],
                pool_contract.functions.collateralToken().call(),
                pool_contract.functions.oracle().call(),
                pool_contract.functions.irm().call(),
                pool_contract.functions.lltv().call(),
            ),
        ))
        vault_shares_balance = vault_contract.functions.position(morpho_market_id,pool_contract.address).call()[0]
    elif config["vaultSharesToken"] != "0x0000000000000000000000000000000000000000":
        vault_shares_contract = w3.eth.contract(address=config["vaultSharesToken"], abi=ERC20_ABI)
        vault_shares_balance = vault_shares_contract.functions.balanceOf(pool_contract.address).call(block_identifier=block_identifier)
    else:  # shares token is null, so we use the base token in its place
        vault_shares_balance = base_token_balance
    short_rewardable_tvl = info['shortsOutstanding']
    lp_rewardable_tvl = vault_shares_balance - short_rewardable_tvl
    if debug:
        print("  === calculated values ===")
        print(f" {'base_token_balance':<31} = {base_token_balance}")
        if "Morpho" in name:
            print(f" {'vault_contract':<31} = {vault_contract_address}")
        print(f" {'vault_shares_balance':<31} = {vault_shares_balance}")
        print(f" {'lp_short_positions':<31} = {lp_short_positions}")
        print(f" {'lp_rewardable_tvl':<31} = {lp_rewardable_tvl}")
        print(f" {'short_rewardable_tvl':<31} = {short_rewardable_tvl}")

    return config, info, name, vault_shares_balance, lp_rewardable_tvl, short_rewardable_tvl

def calculate_spot_price(effective_share_reserves, bond_reserves, initial_vault_share_price, time_stretch):
    """Calculate spot price form effective share reserves and bond reserves.

    Formula is derived as follows:
        p = (y / (mu * (z - zeta))) ** -t_s
        = ((mu * (z - zeta)) / y) ** t_s
        since z_effective = z - zeta
        p = (mu * z_effective / y) ** t_s
    """
    ratio = (initial_vault_share_price * effective_share_reserves) / bond_reserves
    return pow(ratio, time_stretch)

def calculate_apr_from_price(price, duration):
    """Calculate APR from price and duration.

    Formula is:
        r = (1 - p) / (p * t)
    """
    # Convert duration from seconds to years (365 days)
    t = duration / (365 * 24 * 60 * 60)
    return (1 - price) / (price * t)

def calc_apr(config, info):
    """Calculate the spot APR of the pool.

    Args:
        config: Pool configuration
        info: Pool information

    Returns:
        float: The pool's spot APR
    """
    effective_share_reserves = info['shareReserves'] - info['shareAdjustment']
    spot_price = calculate_spot_price(
        effective_share_reserves=effective_share_reserves,
        bond_reserves=info['bondReserves'],
        initial_vault_share_price=config['initialVaultSharePrice']/1e18,
        time_stretch=config['timeStretch']/1e18
    )

    return calculate_apr_from_price(spot_price, config['positionDuration'])

def get_pool_positions(pool_contract, pool_users, pool_ids, lp_rewardable_tvl, short_rewardable_tvl, block = None):
    pool_positions = []
    combined_prefixes = [(0, 3), (2,)]  # Treat prefixes 0 and 3 together, 2 separately
    bal_by_prefix = {0: Decimal(0), 1: Decimal(0), 2: Decimal(0), 3: Decimal(0)}

    # First pass: collect balances
    for user, custom_id in itertools.product(pool_users, pool_ids):
        trade_type, prefix, timestamp = get_trade_details(int(custom_id))
        bal = pool_contract.functions.balanceOf(int(custom_id), user).call(block_identifier=block or "latest")
        if bal > Decimal(1):
            pool_positions.append([user, trade_type, prefix, timestamp, bal, Decimal(0)])
            bal_by_prefix[prefix] += bal

    # Second pass: calculate shares (prefix 1 (longs) get nothing, so we skip it)
    for position in pool_positions:
        prefix = position[2]
        if prefix in [0, 3]:  # assign rewards for LPs and withdrawal shares
            combined_lp_balance = bal_by_prefix[0] + bal_by_prefix[3]  # combine LP and withdrawal share balance
            if combined_lp_balance != Decimal(0):
                share_of_rewardable = position[4] / combined_lp_balance
                position[5] = (lp_rewardable_tvl * share_of_rewardable).quantize(Decimal('0'))
        elif prefix == 2:  # assign rewards for shorts
            if bal_by_prefix[2] != Decimal(0):
                share_of_rewardable = position[4] / bal_by_prefix[2]
                position[5] = (short_rewardable_tvl * share_of_rewardable).quantize(Decimal('0'))

    # Correction step to fix rounding errors
    for prefixes in combined_prefixes:
        combined_shares = sum(position[5] for position in pool_positions if position[2] in prefixes)
        combined_rewardable = lp_rewardable_tvl if prefixes[0] == 0 else short_rewardable_tvl
        if combined_shares != combined_rewardable:
            diff = combined_rewardable - combined_shares
            # Find the position with the largest share among the combined prefixes
            max_position = max((p for p in pool_positions if p[2] in prefixes), key=lambda x: x[5])
            max_position[5] += diff

    return pool_positions

def get_trade_details(asset_id: int) -> tuple[str, int, int]:
    prefix, timestamp = decode_asset_id(asset_id)
    trade_type = HyperdrivePrefix(prefix).name
    return trade_type, prefix, timestamp

def get_tvl_for_pool(w3, pool) -> str:
    pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool), abi=HYPERDRIVE_MORPHO_ABI)
    config, _, name, vault_shares_balance, _, _ = get_pool_details(w3, pool_to_test_contract)
    token_contract_address = config['baseToken'] if config['vaultSharesToken'] == "0x0000000000000000000000000000000000000000" else config['vaultSharesToken']
    token_contract = w3.eth.contract(address=w3.to_checksum_address(token_contract_address), abi=ERC20_ABI)
    tvl_string = f"{name:<58}({pool[:8]}) {vault_shares_balance:>32} {token_contract.functions.symbol().call():>5}"
    return tvl_string

def get_tvl_for_network(w3, network) -> str:
    hyperdrive_registry_contract = w3.eth.contract(address=w3.to_checksum_address(HYPERDRIVE_REGISTRY[network]), abi=HYPERDRIVE_REGISTRY_ABI)
    number_of_instances = hyperdrive_registry_contract.functions.getNumberOfInstances().call()
    instance_list = hyperdrive_registry_contract.functions.getInstancesInRange(0,number_of_instances).call()

    tvl_string = ''
    for pool in instance_list:
        tvl_string += get_tvl_for_pool(w3, pool)

    return tvl_string

def get_instance_list(network, debug=False):
    w3 = create_w3(network)
    registry_address = HYPERDRIVE_REGISTRY[network]
    hyperdrive_registry_contract = w3.eth.contract(address=w3.to_checksum_address(registry_address), abi=HYPERDRIVE_REGISTRY_ABI)
    number_of_instances = hyperdrive_registry_contract.functions.getNumberOfInstances().call()
    if debug:
        print(f"retrieved {number_of_instances} pools on {network}")
    return w3, hyperdrive_registry_contract.functions.getInstancesInRange(0,number_of_instances).call()
