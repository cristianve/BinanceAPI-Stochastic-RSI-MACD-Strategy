import asyncio
import os
import pandas as pd
import numpy as np
import time
import ta

from binance import BinanceSocketManager
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException




# global winrate variables
win = 0
lost = 0

# Dataframe display options
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Init binance API and websocket
api_key = os.environ.get('binance_api')
api_secret = os.environ.get('binance_secret')
client = Client(api_key, api_secret, {"timeout": 20})
bsm = BinanceSocketManager(client, user_timeout=61)


# Transform historical data from API to DataFrame
def getDataFrameFromAPI(symbol, interval, lookback):
    df = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + 'min ago UTC'))
    df = df.iloc[:, :6]
    df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df.set_index('Time')
    df.index = pd.to_datetime(df.index, unit='ms')
    df = df.astype(float)
    return df


# Transform historical data from Websocket to DataFrame
def getDataFrameFromWebsocket(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:, ['s', 'E', 'p']]
    df.columns = ['symbol', 'Time', 'Price']
    df.Price = df.Price.astype(float)
    df.Time = pd.to_datetime(df.Time, unit='ms')
    return df


# Add to DataFrame all technics columns
def applytechnicals(df):
    # Stochastic values
    df['%K'] = ta.momentum.stoch(df.High, df.Low, df.Close, window=14, smooth_window=3)
    df['%D'] = df['%K'].rolling(3).mean()

    # Relative strength index
    df['rsi'] = ta.momentum.rsi(df.Close, window=14)

    # Moving average convergence/divergence
    df['macd'] = ta.trend.macd_diff(df.Close)
    df.dropna(inplace=True)


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
        self.df['Buy'] = np.where(self.df.trigger &
                                  (self.df['%K'].between(20, 80)) & (self.df['%D'].between(20, 80))
                                  & (self.df.rsi > 50) & (self.df.macd > 0), 1, 0)


async def strategy(pair, qty, SL=0.985, TP=1.02, open_position=False):
    global win, lost
    try:
        # Get and transport data from API
        df = getDataFrameFromAPI(pair, '1m', '100')
    except:
        # Try to reconnect after 1 minute
        # delay
        time.sleep(61)
        # Get and transport data from API
        df = getDataFrameFromAPI(pair, '1m', '100')

    # Apply RSI MCAD K-D Technics
    applytechnicals(df)

    # Update decision
    inst = Signals(df, 5)  # lags very important parameter 2, 3 or 5
    inst.decide()

    print(f'[NOT_OPEN_POSITION] Current {pair} Close is ' + str(df.Close.iloc[-1]))
    time.sleep(0.5)

    # Condition to buy
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
        # Receive and transform message from socket
        socket = bsm.trade_socket(pair)
        await socket.__aenter__()
        msg = await socket.recv()
        # {‘e’: ‘error’, ‘m’: ‘Queue overflow. Message not filled’}
        if msg['e'] != "error":
            df = getDataFrameFromWebsocket(msg)

        # SL= 0.985 - 0.015 => 1,5%
        # TP= 1.02  - 0.02 => 2%
        fee = 0.075

        # Take profit sell Price calculation
        buyprice_plus_fee = buyprice + (buyprice * fee)
        final_tp_sell_price = buyprice_plus_fee * TP
        final_tp_sell_price = final_tp_sell_price - (final_tp_sell_price * fee)

        # Stop lost sell Price calculation
        buyprice_minus_fee = buyprice - (buyprice * fee)
        final_sl_sell_price = buyprice_minus_fee * SL
        final_sl_sell_price = final_sl_sell_price - (final_sl_sell_price * fee)

        print(f'[OPEN_POSITION] Current {pair} Close is ' + str(df.Price.iloc[-1]))
        print(f'[OPEN_POSITION] Target - Take profit {pair} is ' + str(final_tp_sell_price))
        print(f'[OPEN_POSITION] Target - Stop loss {pair} is ' + str(final_sl_sell_price))

        # Condition to sell

        if df.Price.iloc[-1] <= final_sl_sell_price or df.Price.iloc[-1] >= final_tp_sell_price:
            order = client.create_order(symbol=pair,
                                        side='SELL',
                                        type='MARKET',
                                        quantity=qty)
            if df.Price.iloc[-1] >= final_tp_sell_price:
                win = win + 1
            if df.Price.iloc[-1] <= final_sl_sell_price:
                lost = lost + 1

            print(f' {win}/{lost} win/lost')
            print(order)
            break



async def main():
    global win, lost
    lost = 0
    win = 0
    symbol = 'ADAUSDT'
    await main_loop(symbol)


async def main_loop(symbol):
    while True:
        await strategy(symbol, 8)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
