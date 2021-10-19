# Binance API 🎮
Try to integrate with Binance API to try simple action like sell/buy via python (PyCharm IDE).


# Python install

```pip install python-binance```


# Security API Keys

Windows cmd command prompt:

set binance_api=your_binance_api_key_here  
set binance_secret=your_api_secret_here

# Strategy
## Buying conditions
* Stochastic %K and %D between 20 & 80
* RSI above 50
* MACD above signal line (diff large 0)


Triggering condition: in the last 'n' time steps %K and %D have to cross below 20

## Selling conditions
* Stop loss-> 99.5% of buying price
* Target profit -> 1.005 % of buying price


## Result 🔍:

![Result](img/Result.JPG)

