library used to evaluate points attribution in Hyperdrive pools.
this attributes rewardable tvl to all users in hyperdrive at a given point in time.

create a .env to point to an RPC node, and set page size for querying events.
see .env.example for an example.

most nodes can only query events across 2000 blocks at a time:
```
ETH_NODE_URL=https://localhost:8545
PAGE_SIZE=2000
```

you can set PAGE_SIZE to a high number like 1000000 only when using Alchemy:
```
ETH_NODE_URL=https://eth-mainnet.g.alchemy.com/v2/XXXXXXXXXXXXXXXXXXXXXXX
PAGE_SIZE=1000000
```

to test for a specific pool, run `test_hyperdrive.py`

modify this line to select the pool:

```
pool_to_test = instance_list[11]  # 5 = ezETH, 3 = sUSDe/DAI, # 6 = eETH, 10 = sUSDS, 11 = sUSDe
```

sample output:
```
number_of_instances=13
=== pool to test: 0x05b65FA90AD702e6Fd0C3Bd7c4c9C47BAB2BEa6b ===
POOL 0x05b65F (ElementDAO 182 Day sUSDe Hyperdrive) CONFIG:
 baseToken                       = 0x4c9EDD5852cd905f086C759E8383e09bff1E68B3
 vaultSharesToken                = 0x9D39A5DE30e57443BfF2A8307A4256c8797A3497
 linkerFactory                   = 0x08B40647714aC1E5742633fC2D83C20D61a199D2
 linkerCodeHash                  = b'Mc\x91Kj3\xd8\x81:VT\xae-\xc9w\xf3~9\x88\x17\xdf%\x19\xd3tW:\xb8Q\xf9\xcb8'
 initialVaultSharePrice          = 1106568265667624251
 minimumShareReserves            = 1000000000000000
 minimumTransactionAmount        = 1000000000000000
 circuitBreakerDelta             = 75000000000000000
 positionDuration                = 15724800
 checkpointDuration              = 86400
 timeStretch                     = 45400439402649528
 governance                      = 0x81758f3361A769016eae4844072FA6d7f828a651
 feeCollector                    = 0x0000000000000000000000000000000000000000
 sweepCollector                  = 0x9eB168Ab44B7c479431681558FdF34230c969DE9
 checkpointRewarder              = 0x0000000000000000000000000000000000000000
 fees                            = (10000000000000000, 250000000000000, 150000000000000000, 30000000000000000)
POOL 0x05b65F (ElementDAO 182 Day sUSDe Hyperdrive) INFO:
 shareReserves                   = 83451168293025296882
 shareAdjustment                 = 66474122431446937445
 zombieBaseProceeds              = 0
 zombieShareReserves             = 0
 bondReserves                    = 85375999138556087124
 lpTotalSupply                   = 90368465319106066473
 vaultSharePrice                 = 1115144996344581378
 longsOutstanding                = 0
 longAverageMaturityTime         = 0
 shortsOutstanding               = 8150000000000000000
 shortAverageMaturityTime        = 1745539200000000000000000000
 withdrawalSharesReadyToWithdraw = 0
 withdrawalSharesProceeds        = 0
 lpSharePrice                    = 1115159980537443763
 longExposure                    = 0
  === calculated values ===
 base_token_balance              = 0
 vault_shares_balance            = 90790332627728876006
 lp_short_positions              = 0
 lp_rewardable_tvl               = 82640332627728876006
 short_rewardable_tvl            = 8150000000000000000
=== ElementDAO 182 Day sUSDe Hyperdrive ===
for prefixes=(0, 3), check combined_shares == combined_rewardable (82640332627728876006 == 82640332627728876006) ✅
for prefixes=(2,), check combined_shares == combined_rewardable (8150000000000000000 == 8150000000000000000) ✅
vault_shares_balance == total_rewardable (90790332627728876006 == 90790332627728876006) ✅
User                                        Type      Prefix    Timestamp     Balance                    Rewardable
0x0000000000000000000000000000000000000000  LP        0         0             1000000000000000           914481974833944
0x9eB168Ab44B7c479431681558FdF34230c969DE9  LP        0         0             90367465319106068480       82639418145754042062
0x9eB168Ab44B7c479431681558FdF34230c969DE9  SHORT     2         1745539200    8150000000000000000        8150000000000000000
Total                                                                         98518465319106068480       90790332627728876006
```

points calculations using this logic:
- ethena: https://github.com/ethena-labs/ethena_sats_adapters/pull/39
- defillama (javascript): https://github.com/DefiLlama/DefiLlama-Adapters/pull/11859
