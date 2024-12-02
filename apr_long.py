# %%
import json
import os

from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

HYPERDRIVE_REGISTRY = {
    "mainnet": "0xbe082293b646cb619a638d29e8eff7cf2f46aa3a",
    "gnosis": "0x666fa9ef9bca174a042c4c306b23ba8ee0c59666",
    "linea": "0x6668310631Ad5a5ac92dC9549353a5BaaE16C666",
    "base": "0x6668310631Ad5a5ac92dC9549353a5BaaE16C666",
}

load_dotenv()

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

    return config, info, name

def calc_apr(config, info):
    effective_share_reserves = info['shareReserves'] - info['shareAdjustment']
    ratio = (config['initialVaultSharePrice']/1e18 * effective_share_reserves) / info['bondReserves']
    spot_price = pow(ratio, config['timeStretch']/1e18)
    t = config['positionDuration'] / (365 * 24 * 60 * 60)
    return (1 - spot_price) / (spot_price * t)

if __name__ == "__main__":
    for network, address in HYPERDRIVE_REGISTRY.items():
        w3 = Web3(Web3.HTTPProvider(f"https://{'eth' if network == 'mainnet' else network}-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_KEY')}"))
        if network == "linea":
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        HYPERDRIVE_REGISTRY_CONTRACT = w3.eth.contract(address=w3.to_checksum_address(address), abi=HYPERDRIVE_REGISTRY_ABI)
        number_of_instances = HYPERDRIVE_REGISTRY_CONTRACT.functions.getNumberOfInstances().call()
        instance_list = HYPERDRIVE_REGISTRY_CONTRACT.functions.getInstancesInRange(0,number_of_instances).call()

        for pool in instance_list:
            pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool), abi=HYPERDRIVE_MORPHO_ABI)
            config, info, name = get_pool_details(pool_to_test_contract)
            apr = calc_apr(config, info)
            print(f"{name:<58}({pool[:8]}) {apr:>6.2%}")
