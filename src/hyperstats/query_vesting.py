# %%
import sys
from datetime import datetime

from hyperstats.constants import (
    VESTING_ABI,
)
from hyperstats.web3_utils import (
    create_w3,
)


def check_vesting_status(w3, vesting_contract_address, recipient_address):
    """Check vesting status for a specific address."""
    try:
        # First verify the contract exists and has code
        code = w3.eth.get_code(vesting_contract_address)
        if len(code) <= 2:  # "0x" or empty
            print(f"\nError: No contract found at {vesting_contract_address}")
            return None

        vesting = w3.eth.contract(address=vesting_contract_address, abi=VESTING_ABI)

        # Try to call a simple view function first
        try:
            info = vesting.functions.recipients(recipient_address).call()
        except Exception as e:
            print(f"\nError: Contract at {vesting_contract_address} doesn't appear to be a vesting contract")
            print(f"Specific error: {str(e)}")
            return None

        status_map = {0: "Terminated", 1: "Paused", 2: "UnPaused"}

        # Get additional amounts
        try:
            claimable = vesting.functions.claimableAmountFor(recipient_address).call()
            locked = vesting.functions.totalLockedOf(recipient_address).call()
        except Exception as e:
            print(f"\nWarning: Could not fetch claimable/locked amounts: {str(e)}")
            claimable = locked = 0

        print(f"\nVesting Status for {recipient_address}:")
        print(f"Status: {status_map[info[7]]}")
        print(f"Start Time: {datetime.fromtimestamp(info[0])}")
        print(f"End Time: {datetime.fromtimestamp(info[1])}")
        print(f"Cliff Duration: {info[2]} seconds")
        print(f"Last Paused At: {datetime.fromtimestamp(info[3]) if info[3] > 0 else 'Never'}")
        print(f"Vesting Rate: {info[4]} tokens/sec")
        print(f"Total Amount: {info[5]}")
        print(f"Total Claimed: {info[6]}")
        print(f"Currently Claimable: {claimable}")
        print(f"Currently Locked: {locked}")

        return info

    except Exception as e:
        print(f"\nError accessing contract: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 4 or len(sys.argv) % 3 == 0:
        print("Usage: python query_vesting.py <network> <vesting_address> <recipient_address> [<network> <vesting_address> <recipient_address> ...]")
        sys.exit(1)

    if len(sys.argv) == 1:
        print("Usage: python query_vesting.py <vesting_address> <recipient_address>")
        sys.exit(1)

    contracts = []
    # Start from index 1 to skip the script name
    for i in range(1, len(sys.argv), 3):
        contracts.append((sys.argv[i], sys.argv[i+1], sys.argv[i+2]))

    for network, address, recipient in contracts:
        w3 = create_w3(network)
        check_vesting_status(
            w3=w3,
            vesting_contract_address=w3.to_checksum_address(address),
            recipient_address=w3.to_checksum_address(recipient)
        )
