# %%
import sys

from dotenv import load_dotenv

from hyperstats.constants import (
    ERC20_ABI,
    SAFE_ABI,
    ZERO_ADDRESS,
)
from hyperstats.utils import get_first_contract_block
from hyperstats.web3_utils import (
    create_w3,
    fetch_events_logs_with_retry,
)

# pylint: disable=bare-except

load_dotenv()

# define contracts we want to query
contracts = {
    "base": "0xbd0f196071de8d7d1521c0ee53584875d2d97fc5",
}

# %%
def format_balance(balance: int, decimals: int) -> str:
    """Format balance with proper decimals."""
    return f"{balance / 10**decimals:.18f}"

def check_contract(w3, address):
    """Check if address is a contract."""
    code = w3.eth.get_code(address)
    return len(code) > 0

def check_safe(w3, address, debug=False):
    """Check if address is a Safe by looking for characteristic Safe functions."""
    is_contract = is_safe = version = owners = threshold = None

    if debug:
        print(f"\nChecking if {address} is a Safe:")
    
    is_contract = check_contract(w3, address)
    if debug:
        print(f"Is {'not ' if not is_contract else ' '}a contract: {is_contract}")

    if is_contract:
        # Check for Safe-specific functions
        safe = w3.eth.contract(address=address, abi=SAFE_ABI)
        try:
            # Try to call Safe-specific functions
            version = safe.functions.VERSION().call()
            owners = safe.functions.getOwners().call()
            threshold = safe.functions.getThreshold().call()
            if debug:
                print("Is a Safe.")
            is_safe = True

        except Exception as exc:
            if debug:
                print(f"Not a Safe: {exc}")
    return is_safe, version, owners, threshold

def get_transfer_logs(w3, contract_address):
    # sanitize address
    contract_address = w3.to_checksum_address(contract_address)

    try:
        # Create pool contract to get LP token address
        pool = w3.eth.contract(address=contract_address, abi=[{
            "stateMutability": "view",
            "type": "function",
            "name": "token",
            "inputs": [],
            "outputs": [{"name": "", "type": "address"}]
        }])
        # Get LP token address
        address_of_interest = pool.functions.token().call()
        print(f"LP Token address: {address_of_interest}")
    except:
        address_of_interest = contract_address

    # get deploy block
    deploy_block, _ = get_first_contract_block(w3, address_of_interest)
    print(f"Deploy block: {deploy_block}")

    # create LP token contract
    contract_of_interest = w3.eth.contract(address=address_of_interest, abi=ERC20_ABI)

    # Track transfer events
    transfer_logs = fetch_events_logs_with_retry(
        contract_event=contract_of_interest.events.Transfer(),
        from_block=deploy_block,
    )
    assert transfer_logs is not None, "error: transfer_logs is None"
    print(f"Found {len(transfer_logs)} Transfer events")

    return transfer_logs, contract_of_interest

def get_holder_stats(transfer_logs, contract_of_interest):
    # Track balances
    balances = {}
    # Process all transfers
    for log in transfer_logs:
        from_addr = log.args['from']
        to_addr = log.args.to
        value = log.args.value

        # Subtract from sender
        if from_addr != ZERO_ADDRESS:
            balances[from_addr] = balances.get(from_addr, 0) - value
            
        # Add to receiver
        if to_addr != ZERO_ADDRESS:
            balances[to_addr] = balances.get(to_addr, 0) + value

    # Filter out zero balances
    current_holders = {addr: balance for addr, balance in balances.items() if balance > 0}

    # Get token decimals
    decimals = contract_of_interest.functions.decimals().call()
    
    print(f"\nTotal current holders: {len(current_holders)}")
    
    # Calculate total supply for percentage
    total_supply = sum(current_holders.values())
    
    # Sort holders by balance
    holders = sorted(current_holders.items(), key=lambda x: x[1], reverse=True)

    return holders, total_supply, decimals

def print_holders(w3, holders, total_supply, decimals):
    print("\nRank\tAddress\t\t\t\t\t\t\tQuantity\t\tPercentage")
    for i, (addr, balance) in enumerate(holders, 1):
        formatted_balance = format_balance(balance, decimals)
        percentage = (balance / total_supply) * 100 if total_supply > 0 else 0

        # Check if address is a Safe
        is_safe_wallet, version, owners, threshold = check_safe(w3, addr, debug=False)
        safe_label = " (Safe)" if is_safe_wallet else "       "

        print(f"{i}\t{addr}{safe_label}\t{formatted_balance}\t{percentage:.4f}%")

        # If it's a Safe, get its info
        if is_safe_wallet:
            print(f"- {threshold}/{len(owners)} Safe (version {version})")
            if owners:
                print("- Owners:")
                for owner in owners:
                    print(f"  - {owner}")

def query(contract_network, contract_address):
    # create network
    w3 = create_w3(contract_network)
    print(contract_network, contract_address)

    transfer_logs, contract_of_interest = get_transfer_logs(w3, contract_address)

    holders, total_supply, decimals = get_holder_stats(transfer_logs, contract_of_interest)

    print_holders(w3, holders, total_supply, decimals)


# %%
if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) % 2 == 0:
        print("Usage: python query_holders.py <network> <address> [<network> <address> ...]")
        sys.exit(1)

    contracts = {}
    # Start from index 1 to skip the script name
    for i in range(1, len(sys.argv), 2):
        contracts[sys.argv[i]] = sys.argv[i+1]

    for network, address in contracts.items():
        query(network, address)
