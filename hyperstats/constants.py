import json
import os
from enum import IntEnum

from dotenv import load_dotenv

load_dotenv()
ETH_NODE_URL = os.getenv("ETH_NODE_URL")
PAGE_SIZE = int(os.getenv("PAGE_SIZE") or 1900)

# mainnet
HYPERDRIVE_REGISTRY_ADDRESS = "0xbe082293b646cb619a638d29e8eff7cf2f46aa3a"

# Get the directory of the current file
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)

# Import relative to the file path of this file
HYPERDRIVE_MORPHO_ABI = None
with open(os.path.join(parent_dir, "abi", "IHyperdriveMorpho.json"), encoding="utf-8") as f:
    HYPERDRIVE_MORPHO_ABI = json.load(f)

HYPERDRIVE_REGISTRY_ABI = None
with open(os.path.join(parent_dir, "abi", "hyperdrive_registry.json"), encoding="utf-8") as f:
    HYPERDRIVE_REGISTRY_ABI = json.load(f)

MORPHO_ABI = None
with open(os.path.join(parent_dir, "abi", "IMorpho.json"), encoding="utf-8") as f:
    MORPHO_ABI = json.load(f)

ERC20_ABI = None
with open(os.path.join(parent_dir, "abi", "ERC20_abi.json"), encoding="utf-8") as f:
    ERC20_ABI = json.load(f)

class HyperdrivePrefix(IntEnum):
    r"""The asset ID is used to encode the trade type in a transaction receipt."""

    LP = 0
    LONG = 1
    SHORT = 2
    WITHDRAWAL_SHARE = 3
