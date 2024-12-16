# %%
import sys
from datetime import datetime

import requests
from lxml import html

from hyperstats.constants import ERC20_ABI, SAFE_ABI, ZERO_ADDRESS
from hyperstats.utils import get_first_contract_block
from hyperstats.web3_utils import create_w3, fetch_events_logs_with_retry, get_bns_name

# pylint: disable=bare-except

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

    # Print latest block and date
    latest_block = w3.eth.get_block(transfer_logs[-1].blockNumber)
    formatted_timestamp = datetime.fromtimestamp(latest_block.timestamp).strftime('%Y-%m-%d %H:%M:%S')

    print(f"Latest block: {latest_block.number} ({formatted_timestamp})")

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

def get_name(w3, address):
    """Get BNS name for an address."""
    return get_bns_name(w3, address)

def get_etherscan_tag(address):
    """Get contract/address label from Etherscan by scraping the webpage."""
    try:
        url = f"https://etherscan.io/address/{address}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            tree = html.fromstring(response.content)
            # Try to get the tag using the XPath
            tag_elements = tree.xpath('/html/body/main/section[3]/div[1]/div[1]/a/div/span')
            if tag_elements:
                tag = tag_elements[0].text_content().strip()
                return tag
    except Exception:
        pass
    return ""

def print_holders(w3, holders, total_supply, decimals, show_all_safe_owners=False):
    print("\nRank\tAddress\t\t\t\t\t\tQuantity\t\tPercentage\tOwner (ENS or [Etherscan tag])")
    for i, (addr, balance) in enumerate(holders, 1):
        formatted_balance = format_balance(balance, decimals)
        percentage = (balance / total_supply) * 100 if total_supply > 0 else 0

        # Check if address is a Safe
        is_safe_wallet, version, owners, threshold = check_safe(w3, addr, debug=False)

        # Get ENS name and Etherscan tag if available
        labels = get_name(w3, addr)
        etherscan_tag = get_etherscan_tag(addr)
        labels += " " if labels else "" + f"[{etherscan_tag}]" if etherscan_tag else ""
        print(f"{i}\t{addr}\t{formatted_balance}\t{percentage:.4f}%\t\t{labels}", end="" if is_safe_wallet else "\n")

        # If it's a Safe, get its info
        if is_safe_wallet:
            if not show_all_safe_owners:
                first_owner = owners[0]
                tag_label = get_name(w3, first_owner)
                owner_tag = get_etherscan_tag(first_owner)
                tag_label += f" [{owner_tag}]" if owner_tag else ""
                print(f"Safe owner: {first_owner}{tag_label}")
            else:
                print(f"\n- {threshold}/{len(owners)} Safe (version {version})")
                if owners:
                    print("- Owners:")
                    for owner in owners:
                        tag_label = get_name(w3, owner)
                        owner_tag = get_etherscan_tag(owner)
                        tag_label += f" [{owner_tag}]" if owner_tag else ""
                        print(f"  - {owner}{f' {tag_label}' if tag_label else ''}")

def query(contract_network, contract_address):
    w3 = create_w3(contract_network)
    print(contract_network, contract_address)

    transfer_logs, contract_of_interest = get_transfer_logs(w3, contract_address)

    holders, total_supply, decimals = get_holder_stats(transfer_logs, contract_of_interest)

    print_holders(w3, holders, total_supply, decimals)

# %% testing
# if __name__ == "__main__":
#     network = "base"
#     address = "0x4426023bbeaC104ea9f6f816c979f4E39C174957"
#     print(f"{address=}")
#     w3 = create_w3(network)
#     provider_url = w3.provider.endpoint_uri.lower()
#     print(f"{provider_url=}")
#     name = get_name(w3, address)
#     print(f"{name=}")

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
