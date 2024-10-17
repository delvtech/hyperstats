# %%
import time
from decimal import Decimal

from hyperstats.constants import (
    HYPERDRIVE_MORPHO_ABI,
    HYPERDRIVE_REGISTRY_ABI,
    HYPERDRIVE_REGISTRY_ADDRESS,
)
from hyperstats.utils import (
    get_hyperdrive_participants,
    get_pool_details,
    get_pool_positions,
)
from hyperstats.web3_utils import w3

## Import
HYPERDRIVE_REGISTRY_CONTRACT = w3.eth.contract(address=w3.to_checksum_address(HYPERDRIVE_REGISTRY_ADDRESS), abi=HYPERDRIVE_REGISTRY_ABI)
number_of_instances = HYPERDRIVE_REGISTRY_CONTRACT.functions.getNumberOfInstances().call()
print(f"{number_of_instances=}")
instance_list = HYPERDRIVE_REGISTRY_CONTRACT.functions.getInstancesInRange(0,number_of_instances).call()

pool_to_test = instance_list[0]  # 5 = ezETH, 3 = sUSDe/DAI, # 6 = eETH, 10 = sUSDS
print(f"=== pool to test: {pool_to_test} ===")
start_time = time.time()
pool_users, pool_ids = get_hyperdrive_participants(pool_to_test, cache=False)
pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool_to_test), abi=HYPERDRIVE_MORPHO_ABI)
config, info, name, vault_shares_balance, lp_rewardable_tvl, short_rewardable_tvl = get_pool_details(pool_to_test_contract, debug=True)
print(f"=== {name} ===")
pool_positions = get_pool_positions(
    pool_contract=pool_to_test_contract,
    pool_users=pool_users,
    pool_ids=pool_ids,
    lp_rewardable_tvl=lp_rewardable_tvl,
    short_rewardable_tvl=short_rewardable_tvl,
    debug=True,
)

# display stuff
total_balance = sum(position[4] for position in pool_positions)
total_rewardable = sum(position[5] for position in pool_positions)

if vault_shares_balance == Decimal(total_rewardable):
    print(f"vault_shares_balance == total_rewardable ({vault_shares_balance} == {total_rewardable}) ✅")
else:
    print(f"vault_shares_balance != total_rewardable ({vault_shares_balance} != {total_rewardable}) ❌")

print("User\tType\tPrefix\tTimestamp\tBalance\tRewardable")  # Header
for position in pool_positions:
    # print(f"{position[0]}\t{position[1]}\t{position[2]}\t{position[3]}\t{position[4]}\t{position[5]}")
    print('\t'.join(map(str, position)))
print(f"Total\t\t\t\t{total_balance}\t{total_rewardable}")  # Subtotals
