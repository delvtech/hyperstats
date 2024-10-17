# %%
import json
import os

import eth_abi
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

HYPERDRIVE_REGISTRY_ADDRESS = "0xbe082293b646cb619a638d29e8eff7cf2f46aa3a"

# Get the directory of the current file
current_dir = os.path.dirname(__file__)

ERC20_ABI = None
with open(os.path.join(current_dir, "src", "abi", "ERC20_abi.json"), encoding="utf-8") as f:
    ERC20_ABI = json.load(f)

HYPERDRIVE_MORPHO_ABI = None
with open(os.path.join(current_dir, "src", "abi", "IHyperdriveMorpho.json"), encoding="utf-8") as f:
    HYPERDRIVE_MORPHO_ABI = json.load(f)

HYPERDRIVE_REGISTRY_ABI = None
with open(os.path.join(current_dir, "src", "abi", "hyperdrive_registry.json"), encoding="utf-8") as f:
    HYPERDRIVE_REGISTRY_ABI = json.load(f)

MORPHO_ABI = None
with open(os.path.join(current_dir, "src", "abi", "IMorpho.json"), encoding="utf-8") as f:
    MORPHO_ABI = json.load(f)

ETH_NODE_URL = os.getenv("ETH_NODE_URL")

# pylint: disable=redefined-builtin

# defaults to http://localhost:8545 if you don't set ETH_NODE_URL
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

def get_pool_details(pool_contract, debug: bool = False, block_number: int | None = None):
    name = pool_contract.functions.name().call()
    config_values = pool_contract.functions.getPoolConfig().call()
    config_outputs = pool_contract.functions.getPoolConfig().abi['outputs'][0]['components']
    config_keys = [i['name'] for i in config_outputs if 'name' in i]
    config = dict(zip(config_keys, config_values))
    if debug:
        print(f"POOL {pool_contract.address[:8]} ({name}) CONFIG:")
        for k,i in config.items():
            print(f" {k:<31} = {i}")
    info_values = pool_contract.functions.getPoolInfo().call(block_identifier=block_number or "latest")
    info_outputs = pool_contract.functions.getPoolInfo().abi['outputs'][0]['components']
    info_keys = [i['name'] for i in info_outputs if 'name' in i]
    info = dict(zip(info_keys, info_values))
    if debug:
        print(f"POOL {pool_contract.address[:8]} ({name}) INFO:")
        for k,i in info.items():
            print(f" {k:<31} = {i}")
    lp_short_positions = info['longExposure']

    # query pool holdings of the base token
    base_token_balance = None
    if config["baseToken"] == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE":
        # the base token is ETH
        base_token_balance = w3.eth.get_balance(pool_contract.address)
    else:
        base_token_contract = w3.eth.contract(address=config["baseToken"], abi=ERC20_ABI)
        base_token_balance = base_token_contract.functions.balanceOf(pool_contract.address).call()
    vault_shares_balance = vault_contract_address = vault_contract = vault_shares_contract = None
    if "Morpho" in name:
        vault_contract_address = pool_contract.functions.vault().call()
        vault_contract = w3.eth.contract(address=vault_contract_address, abi=MORPHO_ABI)
        packed_ids = eth_abi.encode(  # type: ignore
            ("address", "address", "address", "address", "uint256"),
            (
                config["baseToken"],
                pool_contract.functions.collateralToken().call(),
                pool_contract.functions.oracle().call(),
                pool_contract.functions.irm().call(),
                pool_contract.functions.lltv().call(),
            ),
        )
        morpho_market_id = w3.keccak(packed_ids)
        vault_shares_balance = vault_contract.functions.position(morpho_market_id,pool_contract.address).call()[0]
    elif config["vaultSharesToken"] != "0x0000000000000000000000000000000000000000":
        vault_shares_contract = w3.eth.contract(address=config["vaultSharesToken"], abi=ERC20_ABI)
        vault_shares_balance = vault_shares_contract.functions.balanceOf(pool_contract.address).call()
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

## Import
HYPERDRIVE_REGISTRY_CONTRACT = w3.eth.contract(address=w3.to_checksum_address(HYPERDRIVE_REGISTRY_ADDRESS), abi=HYPERDRIVE_REGISTRY_ABI)
number_of_instances = HYPERDRIVE_REGISTRY_CONTRACT.functions.getNumberOfInstances().call()
instance_list = HYPERDRIVE_REGISTRY_CONTRACT.functions.getInstancesInRange(0,number_of_instances).call()

for pool_to_test in instance_list:
    pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool_to_test), abi=HYPERDRIVE_MORPHO_ABI)
    config, info, name, vault_shares_balance, lp_rewardable_tvl, short_rewardable_tvl = get_pool_details(pool_to_test_contract)
    token_contract_address = config['baseToken'] if config['vaultSharesToken'] == "0x0000000000000000000000000000000000000000" else config['vaultSharesToken']
    token_contract = w3.eth.contract(address=w3.to_checksum_address(token_contract_address), abi=ERC20_ABI)
    print(f"{name:<58}({pool_to_test[:8]}) {vault_shares_balance:>32} {token_contract.functions.symbol().call():>5}")
