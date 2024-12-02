import json
import os
from enum import IntEnum

from dotenv import load_dotenv

load_dotenv()
ALCHEMY_KEY = os.getenv("ALCHEMY_KEY")
PAGE_SIZE = int(os.getenv("PAGE_SIZE") or 1900)

# mainnet
HYPERDRIVE_REGISTRY = {
    "mainnet": "0xbe082293b646cb619a638d29e8eff7cf2f46aa3a",
    "gnosis": "0x666fa9ef9bca174a042c4c306b23ba8ee0c59666",
    "linea": "0x6668310631Ad5a5ac92dC9549353a5BaaE16C666",
    "base": "0x6668310631Ad5a5ac92dC9549353a5BaaE16C666",
}

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

HYPERDRIVE_FACTORY_ABI = None
with open(os.path.join(parent_dir, "abi", "Factory.json"), encoding="utf-8") as f:
    HYPERDRIVE_FACTORY_ABI = json.load(f)

class HyperdrivePrefix(IntEnum):
    r"""The asset ID is used to encode the trade type in a transaction receipt."""

    LP = 0
    LONG = 1
    SHORT = 2
    WITHDRAWAL_SHARE = 3
