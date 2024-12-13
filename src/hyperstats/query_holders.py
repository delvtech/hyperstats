# %%
from dotenv import load_dotenv

from hyperstats.constants import (
    ERC20_ABI,
)
from hyperstats.utils import get_first_contract_block
from hyperstats.web3_utils import (
    create_w3,
    fetch_events_logs_with_retry,
)

load_dotenv()

# define contracts we want to query
contracts = {
    "base": "0xbd0f196071de8d7d1521c0ee53584875d2d97fc5",
}

# %%
def format_balance(balance: int, decimals: int) -> str:
    """Format balance with proper decimals."""
    return f"{balance / 10**decimals:.18f}"

for contract_network, pool_address in contracts.items():
    # create network
    w3 = create_w3(contract_network)
    print(contract_network, pool_address)

    # sanitize address
    pool_address = w3.to_checksum_address(pool_address)

    # Create pool contract to get LP token address
    pool = w3.eth.contract(address=pool_address, abi=[{
        "stateMutability": "view",
        "type": "function",
        "name": "token",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}]
    }])
    
    # Get LP token address
    lp_token_address = pool.functions.token().call()
    print(f"LP Token address: {lp_token_address}")

    # get deploy block
    deploy_block, extra_data = get_first_contract_block(w3, pool_address)
    print(f"Deploy block: {deploy_block}")

    # create LP token contract
    lp_token = w3.eth.contract(address=lp_token_address, abi=ERC20_ABI)

    # Track transfer events
    transfer_logs = fetch_events_logs_with_retry(
        contract_event=lp_token.events.Transfer(),
        from_block=deploy_block,
    )
    assert transfer_logs is not None, "error: transfer_logs is None"
    print(f"Found {len(transfer_logs)} Transfer events")

    # Track balances
    balances = {}
    
    # Process all transfers
    for log in transfer_logs:
        from_addr = log.args['from']
        to_addr = log.args.to
        value = log.args.value

        # Subtract from sender
        if from_addr != '0x0000000000000000000000000000000000000000':
            balances[from_addr] = balances.get(from_addr, 0) - value
            
        # Add to receiver
        if to_addr != '0x0000000000000000000000000000000000000000':
            balances[to_addr] = balances.get(to_addr, 0) + value

    # Filter out zero balances
    current_holders = {addr: balance for addr, balance in balances.items() if balance > 0}

    # Get token decimals
    decimals = lp_token.functions.decimals().call()
    
    print(f"\nTotal current holders: {len(current_holders)}")
    
    # Calculate total supply for percentage
    total_supply = sum(current_holders.values())
    
    # Sort holders by balance
    sorted_holders = sorted(current_holders.items(), key=lambda x: x[1], reverse=True)
    
    print("\nRank\tAddress\t\t\t\t\t\tQuantity\t\tPercentage")
    for i, (addr, balance) in enumerate(sorted_holders, 1):
        formatted_balance = format_balance(balance, decimals)
        percentage = (balance / total_supply) * 100 if total_supply > 0 else 0
        print(f"{i}\t{addr}\t{formatted_balance}\t{percentage:.4f}%")

# %%
