# Binance API ๐ฎ
Tranding bot using Binance API - Stochastic, RSI and MACD Strategy ๐๐

# Objectives ๐น

1- Try to integrate with Binance API to try simple action like sell/buy via python (PyCharm IDE), using BinanceAPI Documentation for the first time ๐ค.

https://binance-docs.github.io/apidocs

2- Make some simple strategy and run with real funds.

# Python install โ

```pip install python-binance```


# Security API Keys ๐

Windows cmd command prompt:

set binance_api=your_binance_api_key_here  
set binance_secret=your_api_secret_here

# Strategy๐
## Buying conditions ๐โ๏ธ
* Stochastic %K and %D between 20 & 80
* RSI above 50
* MACD above signal line (diff large 0)


Triggering condition: in the last 'n' time steps %K and %D have to cross below 20

## Selling conditions ๐โ
* Stop loss-> 99.5% of buying price
* Target profit -> 1.005 % of buying price

# Accuracy โ๏ธ

//TODO try to calculate % of accuracy if we execute this strategy along time


## Result ๐:

![Result](img/Result.JPG)

