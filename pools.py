# %%
import sys

from hyperstats.constants import (
    ERC20_ABI,
    HYPERDRIVE_MORPHO_ABI,
    HYPERDRIVE_REGISTRY,
)
from hyperstats.utils import calc_apr, get_instance_list, get_pool_details, get_hyperdrive_participants

# print headers
print(f"{'network':<10} {'pool':<58} ({'address'}) {'balance':>32} {'token':>14} {'APR':>6} ")

def display_pool(w3, pool, network):
    _, _, deployment_block, extra_data = get_hyperdrive_participants(w3, pool, cache=False)
    pool_contract = w3.eth.contract(address=w3.to_checksum_address(pool), abi=HYPERDRIVE_MORPHO_ABI)
    config, info, name, vault_shares_balance, _, _ = get_pool_details(w3, pool_contract, deployment_block, extra_data)
    token_contract_address = config['baseToken'] if config['vaultSharesToken'] == "0x0000000000000000000000000000000000000000" else config['vaultSharesToken']
    token_contract = w3.eth.contract(address=w3.to_checksum_address(token_contract_address), abi=ERC20_ABI)
    symbol = token_contract.functions.symbol().call()
    apr = calc_apr(config, info)
    print(f"{network:<10} {name:<58}({pool[:8]}) {vault_shares_balance:>32} {symbol:>14} {apr:>6.2%} ")

if __name__ == "__main__":
    networks = sys.argv[1] if len(sys.argv) > 1 else "all"
    if networks == "all":
        networks = list(HYPERDRIVE_REGISTRY.keys())
    if not isinstance(networks, list):
        networks = [networks]
    for network in networks:
        w3, instance_list = get_instance_list(network, debug=False)
        pool = sys.argv[2] if len(sys.argv) > 2 else "all"
        if pool == "all":
            for idx, pool in enumerate(instance_list):
                display_pool(w3, pool, network)
        else:
            display_pool(w3, instance_list[int(pool)], network)
