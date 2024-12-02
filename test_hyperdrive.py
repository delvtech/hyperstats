# %%
import sys
from decimal import Decimal

from hyperstats.constants import (
    HYPERDRIVE_MORPHO_ABI,
    HYPERDRIVE_REGISTRY,
)
from hyperstats.utils import (
    calc_apr,
    get_hyperdrive_participants,
    get_instance_list,
    get_pool_details,
    get_pool_positions,
)


def test_instance(w3, pool_to_test):
    pool_users, pool_ids, deployment_block, extra_data = get_hyperdrive_participants(w3, pool_to_test, cache=False)
    pool_to_test_contract = w3.eth.contract(address=w3.to_checksum_address(pool_to_test), abi=HYPERDRIVE_MORPHO_ABI)
    config, info, name, vault_shares_balance, lp_rewardable_tvl, short_rewardable_tvl = get_pool_details(w3, pool_to_test_contract, deployment_block, extra_data, debug=True)

    print(f"=== {name} ===")
    apr = calc_apr(config, info)
    print(f"APR: {apr:.2%}")
    pool_positions = get_pool_positions(
        pool_contract=pool_to_test_contract,
        pool_users=pool_users,
        pool_ids=pool_ids,
        lp_rewardable_tvl=lp_rewardable_tvl,
        short_rewardable_tvl=short_rewardable_tvl,
    )

    # Make sure rewards add up to rewardable TVL
    combined_prefixes = [(0, 3), (2,)]  # Treat prefixes 0 and 3 together, 2 separately
    for prefixes in combined_prefixes:
        combined_shares = sum(position[5] for position in pool_positions if position[2] in prefixes)
        combined_rewardable = lp_rewardable_tvl if prefixes[0] == 0 else short_rewardable_tvl
        if combined_shares == combined_rewardable:
            print(f"for prefixes={prefixes}, check combined_shares == combined_rewardable ({combined_shares} == {combined_rewardable}) ✅")
        else:
            print(f"for prefixes={prefixes}, check combined_shares == combined_rewardable ({combined_shares} != {combined_rewardable}) ❌")

    # test totals
    total_balance = sum(position[4] for position in pool_positions)
    total_rewardable = sum(position[5] for position in pool_positions)
    if vault_shares_balance == Decimal(total_rewardable):
        print(f"vault_shares_balance == total_rewardable ({vault_shares_balance} == {total_rewardable}) ✅")
    else:
        print(f"vault_shares_balance != total_rewardable ({vault_shares_balance} != {total_rewardable}) ❌")

    # ensure total_rewardable is positive
    if total_rewardable > Decimal(0):
        print(f"total_rewardable is positive ({total_rewardable}) ✅")
    else:
        print(f"total_rewardable is not positive ({total_rewardable}) ❌")

    # Print results
    # Define column widths
    col_widths = [42, 8, 8, 12, 25, 25]

    # Print header
    header = ["User", "Type", "Prefix", "Timestamp", "Balance", "Rewardable"]
    print("  ".join(f"{h:<{w}}" for h, w in zip(header, col_widths)))

    # Print data rows
    for position in pool_positions:
        row = [
            position[0],
            position[1],
            position[2],
            position[3],
            f"{position[4]:.0f}",
            f"{position[5]:.0f}"
        ]
        print("  ".join(f"{str(item):<{w}}" for item, w in zip(row, col_widths)))

    # Print total
    total_row = ["Total", "", "", "", f"{total_balance:.0f}", f"{total_rewardable:.0f}"]
    print("  ".join(f"{str(item):<{w}}" for item, w in zip(total_row, col_widths)))

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
                print(f"=== {network} pool {idx:>2}: {pool} ===")
                test_instance(w3, pool)
        else:
            test_instance(w3, instance_list[int(pool)])  # 5 = ezETH, 3 = sUSDe/DAI, # 6 = eETH, 10 = sUSDS, 11 = sUSDe
