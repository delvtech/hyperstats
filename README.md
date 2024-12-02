library used to evaluate points attribution in Hyperdrive pools.
this attributes rewardable tvl to all users in hyperdrive at a given point in time.

create a .env with an alchemy key. see .env.example for an example.

to test, run `test_hyperdrive.py`:
- for all pools: `python test_hyperdrive.py`
- for all pools on gnosis: `python test_hyperdrive.py gnosis`
- for the pool with index 4 on base (first index is 0): `python test_hyperdrive.py base 4`

example:
```
python test_hyperdrive.py mainnet 11
retrieved 13 pools on mainnet
CONFIG:
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
 deploymentBlock                 = 20931644
 extraData                       = b''
INFO:
 shareReserves                   = 83451168293025296882
 shareAdjustment                 = 66474122431446937445
 zombieBaseProceeds              = 0
 zombieShareReserves             = 0
 bondReserves                    = 85375999138556087124
 lpTotalSupply                   = 90368465319106066473
 vaultSharePrice                 = 1128477904657301931
 longsOutstanding                = 0
 longAverageMaturityTime         = 0
 shortsOutstanding               = 8150000000000000000
 shortAverageMaturityTime        = 1745539200000000000000000000
 withdrawalSharesReadyToWithdraw = 0
 withdrawalSharesProceeds        = 0
 lpSharePrice                    = 1128086447882534086
 longExposure                    = 0
  === calculated values ===
 base_token_balance              = 0
 vault_shares_balance            = 90790332627728876006
 lp_short_positions              = 0
 lp_rewardable_tvl               = 82640332627728876006
 short_rewardable_tvl            = 8150000000000000000
=== ElementDAO 182 Day sUSDe Hyperdrive ===
APR: 14.27%
for prefixes=(0, 3), check combined_shares == combined_rewardable (82640332627728876006 == 82640332627728876006) ✅
for prefixes=(2,), check combined_shares == combined_rewardable (8150000000000000000 == 8150000000000000000) ✅
vault_shares_balance == total_rewardable (90790332627728876006 == 90790332627728876006) ✅
total_rewardable is positive (90790332627728876006) ✅
User                                        Type      Prefix    Timestamp     Balance                    Rewardable
0x9eB168Ab44B7c479431681558FdF34230c969DE9  LP        0         0             90367465319106068480       82639418145754042062
0x9eB168Ab44B7c479431681558FdF34230c969DE9  SHORT     2         1745539200    8150000000000000000        8150000000000000000
0x0000000000000000000000000000000000000000  LP        0         0             1000000000000000           914481974833944
Total                                                                         98518465319106068480       90790332627728876006
```

points calculations using this logic:
- ethena: https://github.com/ethena-labs/ethena_sats_adapters/pull/39
- defillama (javascript): https://github.com/DefiLlama/DefiLlama-Adapters/pull/11859
