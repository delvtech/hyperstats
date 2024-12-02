# %%

from hyperstats.constants import (
    ERC20_ABI,
    HYPERDRIVE_MORPHO_ABI,
)
from hyperstats.utils import get_instance_list, get_pool_details

w3, instance_list = get_instance_list("mainnet")

for pool_to_test in instance_list:
    pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool_to_test), abi=HYPERDRIVE_MORPHO_ABI)
    config, info, name, vault_shares_balance, lp_rewardable_tvl, short_rewardable_tvl = get_pool_details(w3, pool_to_test_contract)
    token_contract_address = config['baseToken'] if config['vaultSharesToken'] == "0x0000000000000000000000000000000000000000" else config['vaultSharesToken']
    token_contract = w3.eth.contract(address=w3.to_checksum_address(token_contract_address), abi=ERC20_ABI)
    print(f"{name:<58}({pool_to_test[:8]}) {vault_shares_balance:>32} {token_contract.functions.symbol().call():>5}")
