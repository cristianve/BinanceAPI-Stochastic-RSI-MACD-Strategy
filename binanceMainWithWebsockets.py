import asyncio
import os

#python -m pip install python-binance


from binance import BinanceSocketManager
from binance.client import Client
import pandas as pd
import numpy as np
import time
import ta
from binance.exceptions import BinanceAPIException, BinanceOrderException

pd.set_option('display.max_rows', None)
# Set it to None to display all columns in the dataframe
pd.set_option('display.max_columns', None)

# Width of the display in characters. If set to None and pandas will correctly auto-detect the width.
pd.set_option('display.width', None)

# init
api_key = os.environ.get('binance_api')
api_secret = os.environ.get('binance_secret')

client = Client(api_key, api_secret, {"timeout": 20})
bsm = BinanceSocketManager(client)
# client.API_URL = 'https://testnet.binance.vision/api'


################ USER INFO ################

# get balances for all assets & some account information
print(client.get_account())

# get balance for a specific asset only (BTC)
print(client.get_asset_balance(asset='ADA'))
print(client.get_asset_balance(asset='BNB'))

# get balances for futures account
#print(client.futures_account_balance())

# get balances for margin account
#print(client.get_margin_account())


# get latest price from Binance API
btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
# print full output (dictionary)
#print("Last BTC PRICE:")
#print(btc_price)
#print(btc_price["price"])


# get historical data table
def getminutedata(symbol, interval, lookback):
    frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + 'min ago UTC'))
    frame = frame.iloc[:, :6]
    frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    frame = frame.set_index('Time')
    frame.index = pd.to_datetime(frame.index, unit='ms')
    frame = frame.astype(float)
    return frame


# get BTC USDT interval 1 minute 100 times
df = getminutedata('ADAUSDT', '1m', '100')


def applytechnicals(df):
    # Stochastic values
    df['%K'] = ta.momentum.stoch(df.High, df.Low, df.Close, window=14, smooth_window=3)
    df['%D'] = df['%K'].rolling(3).mean()

    # Relative strength index
    df['rsi'] = ta.momentum.rsi(df.Close, window=14)

    # Moving average convergence/divergence
    df['macd'] = ta.trend.macd_diff(df.Close)
    df.dropna(inplace=True)


applytechnicals(df)


# print(df)


class Signals:
    def __init__(self, df, lags):
        self.df = df
        self.lags = lags

    def gettrigger(self):
        dfx = pd.DataFrame()
        for i in range(self.lags + 1):
            mask = (self.df['%K'].shift(i) < 20) & (self.df['%D'].shift(i) < 20)
            dfx = dfx.append(mask, ignore_index=True)
        return dfx.sum(axis=0)

    def decide(self):
        self.df['trigger'] = np.where(self.gettrigger(), 1, 0)
        self.df['Buy'] = np.where((self.df.trigger) &
    (self.df['%K'].between(20, 80)) & (self.df['%D'].between(20, 80))
                                   & (self.df.rsi > 50) & (self.df.macd > 0), 1, 0)


#inst = Signals(df, 5)
#inst.decide()
# take only buy equals True
#df = df[df.Buy == 1]
#print(df)

def createframe(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:, ['s', 'E', 'p']]
    df.columns = ['symbol', 'Time', 'Price']
    df.Price = df.Price.astype(float)
    df.Time = pd.to_datetime(df.Time, unit='ms')
    return df



async def strategy(pair, qty, open_position=False):
    df = getminutedata(pair, '1m', '100')
    applytechnicals(df)
    inst = Signals(df, 5) #lags very important parameter 2, 3 or 5
    inst.decide()
    print(f'current Close is ' + str(df.Close.iloc[-1]))

    socket = bsm.trade_socket(pair)
    if df.Buy.iloc[-1]:
        try:
            order = client.create_order(symbol=pair,
                                        side='BUY',
                                        type='MARKET',
                                        quantity=qty)
            print(order)
            buyprice = float(order['fills'][0]['price'])
            open_position = True

        except BinanceAPIException as e:
            # error handling goes here
            print(e)
        except BinanceOrderException as e:
            # error handling goes here
            print(e)


    while open_position:
        await socket.__aenter__()
        msg = await socket.recv()
        df = createframe(msg)
        #df = getminutedata(pair, '1m', '2')

        print(f'current Close ' + str(df.Close.iloc[-1]))
        print(f'current Target ' + str(buyprice * 1.005))
        print(f'current Stop is ' + str(buyprice * 0.995))
        if df.Close[-1] <= buyprice * 0.995 or df.Close[-1] >= 1.005 * buyprice:
            order = client.create_order(symbol=pair,
                                        side='SELL',
                                        type='MARKET',
                                        quantity=qty)
            print(order)
            break


async def main():
    while True:
            await strategy('ADAUSDT', 8)


if __name__ ==  "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())



