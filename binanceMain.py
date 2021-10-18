import os

from binance.client import Client

# init
api_key = os.environ.get('binance_api')
api_secret = os.environ.get('binance_secret')

client = Client(api_key, api_secret)

#client.API_URL = 'https://testnet.binance.vision/api'


################ USER INFO ################

# get balances for all assets & some account information
print(client.get_account())

# get balance for a specific asset only (BTC)
print(client.get_asset_balance(asset='ADA'))
print(client.get_asset_balance(asset='BNB'))

# get balances for futures account
print(client.futures_account_balance())

# get balances for margin account
#print(client.get_margin_account())


# get latest price from Binance API
btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
# print full output (dictionary)
print("Last BTC PRICE:")
print(btc_price)
print(btc_price["price"])