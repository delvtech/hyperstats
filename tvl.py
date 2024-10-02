# %%

from constants import (
    ERC20_ABI,
    HYPERDRIVE_MORPHO_ABI,
    HYPERDRIVE_REGISTRY_ABI,
    HYPERDRIVE_REGISTRY_ADDRESS,
)
from utils import get_pool_details
from web3_utils import w3

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
