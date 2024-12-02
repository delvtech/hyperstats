library used to evaluate points attribution in Hyperdrive pools.
this attributes rewardable tvl to all users in hyperdrive at a given point in time.

create a .env with an alchemy key. see .env.example for an example.

to retrieve data on pools, run `pools.py`:
- for all pools: `python pools.py`
- for all pools on gnosis: `python pools.py gnosis`
- for the pool with index 4 on base (first index is 0): `python pools.py base 4`

example:
```
python pools.py
network    pool                                                       (address)                          balance          token    APR 
mainnet    ElementDAO 182 Day stETH Hyperdrive                       (0xd7e470)            438318865515317591364          stETH  3.03% 
mainnet    ElementDAO 182 Day sDAI Hyperdrive                        (0x324395)          22955725560726037384130           sDAI  6.94% 
mainnet    ElementDAO 182 Day rETH Hyperdrive                        (0xca5dB9)               179373942174642300           rETH  2.77% 
mainnet    ElementDAO 182 Day Morpho Blue sUSDe/DAI Hyperdrive       (0xd41225)     2304981772640789236524015961            DAI  7.24% 
mainnet    ElementDAO 182 Day Morpho Blue USDe/DAI Hyperdrive        (0xA29A77)       94282514240134303017396434            DAI  7.50% 
mainnet    ElementDAO 182 Day ezETH Hyperdrive                       (0x4c3054)                57567896791253199          ezETH  3.80% 
mainnet    ElementDAO 182 Day ether.fi eETH Hyperdrive               (0x158Ed8)             17163019069094516532           eETH  3.84% 
mainnet    ElementDAO 182 Day Morpho Blue wstETH/USDC Hyperdrive     (0xc8D47D)                   95900401063915           USDC  4.00% 
mainnet    ElementDAO 182 Day Morpho Blue wstETH/USDA Hyperdrive     (0x7548c4)       98667961716192300145978972           USDA  3.50% 
mainnet    ElementDAO 182 Day stUSD Hyperdrive                       (0xA40901)             94956970000216197387          stUSD  6.66% 
mainnet    ElementDAO 182 Day sUSDS Hyperdrive                       (0x8f2AC1)             99743859690519536748          sUSDS  6.25% 
mainnet    ElementDAO 182 Day sUSDe Hyperdrive                       (0x05b65F)             90790332627728876006          sUSDe 14.27% 
mainnet    ElementDAO 182 Day sGYD Hyperdrive                        (0xf1232D)             68274325432472522796           sGYD 11.83% 
gnosis     ElementDAO 182 Day wstETH Hyperdrive                      (0x2f840f)            370030002237625648356         wstETH  2.90% 
gnosis     ElementDAO 182 Day sxDAI Hyperdrive                       (0xEe9BFf)         360384952128727400943727           sDAI  8.24% 
gnosis     ElementDAO 182 Day sGYD Hyperdrive                        (0x9248f8)            100000000000000000000           sGYD 10.00% 
linea      ElementDAO 182 Day KelpDAO rsETH Hyperdrive               (0xB56e0B)               416554361594590672         wrsETH 18.29% 
linea      ElementDAO 182 Day Renzo xezETH Hyperdrive                (0x1cB0E9)                51848668338140542          ezETH  3.02% 
base       ElementDAO 182 Day cbETH Hyperdrive                       (0x2a1ca3)                30000000000000000          cbETH  3.00% 
base       ElementDAO 182 Day Morpho Blue cbETH/USDC Hyperdrive      (0xFcdaF9)                  109838602795218           USDC  0.98% 
base       ElementDAO 30 Day Num Finance snARS Hyperdrive            (0x1243C0)       34569406873179703000133427          snARS 44.80% 
base       ElementDAO 182 Day Moonwell ETH Hyperdrive                (0xceD9F8)                29882870206523178          mwETH  8.00% 
base       ElementDAO 91 Day Aerodrome LP AERO-USDC Hyperdrive       (0x9bAdB6)                     805376171089 vAMM-USDC/AERO 48.50% 
base       ElementDAO 182 Day Moonwell USDC Hyperdrive               (0xD9b66D)             99585394320722868152         mwUSDC 10.00% 
base       ElementDAO 182 Day Moonwell EURC Hyperdrive               (0xdd8E1B)             99925000860169472298         mwEURC 10.00%
```

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
