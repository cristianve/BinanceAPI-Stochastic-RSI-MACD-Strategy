import pandas as pd
import os
import numpy as np
import ta

from binance import BinanceSocketManager
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# Dataframe display options
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# Init binance API and websocket
api_key = os.environ.get('binance_api')
api_secret = os.environ.get('binance_secret')
client = Client(api_key, api_secret, {"timeout": 20})
bsm = BinanceSocketManager(client, user_timeout=61)

SL = 0.95
TP = 1.05


# Transform historical data from API to DataFrame
def getDataFrameFromAPI(symbol, interval, lookback):
    df = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback))
    df = df.iloc[:, :6]
    df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df.set_index('Time')
    df.index = pd.to_datetime(df.index, unit='ms')
    df = df.astype(float)
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


def main():
    df = getDataFrameFromAPI('ADAUSDT', Client.KLINE_INTERVAL_5MINUTE, '1 month ago UTC')

    # Apply RSI MCAD K-D Technics
    applytechnicals(df)

    # Update decision
    inst = Signals(df, 3)  # lags very important parameter 2, 3 or 5
    inst.decide()

    # when trigger / buy == 1

    Buying_date = []
    Selling_date = []

    win = 0
    lost = 0

    amount = 100

    for i in range(len(df)):
        if df.Buy.iloc[i]:
            print('Enter', df.index[i])
            buyprice = df.Close.iloc[i]
            Buying_date.append(df.index[i])
            open_position = True
            j = i

            while (open_position and j < len(df)):
                fee = 0.075 / 100

                # Stop lost sell Price calculation
                buyprice_minus_fee = buyprice - (buyprice * fee)
                final_sl_sell_price = buyprice_minus_fee * SL
                final_sl_sell_price = final_sl_sell_price - (final_sl_sell_price * fee)

                # Take profit sell Price calculation
                buyprice_plus_fee = buyprice + (buyprice * fee)
                final_tp_sell_price = buyprice_plus_fee * TP
                final_tp_sell_price = final_tp_sell_price - (final_tp_sell_price * fee)

                if df.Close.iloc[j] >= final_tp_sell_price:
                    print('[WIN] -Open position at: ', buyprice,
                          'Buy Price + fee:', buyprice_plus_fee,
                          'Final TP price:', final_tp_sell_price)

                    Selling_date.append(df.index[j])
                    win = win + 1
                    open_position = False
                if df.Close.iloc[j] <= final_sl_sell_price:
                    print('[LOST] - Open position at: ', buyprice,
                          'Buy Price - fee:', buyprice_minus_fee,
                          'SL price:', final_sl_sell_price)
                    Selling_date.append(df.index[j])
                    lost = lost + 1
                    open_position = False
                j = j + 1

    print('Wins:', win)
    print('Lost:', lost)
    print("Buying:", Buying_date)
    print("Selling:", Selling_date)
    print('Winrate', win / (win + lost) * 100)
    amount = amount + (win * 0.10)
    amount = amount - (lost * 0.10)
    print(amount)

if __name__ == "__main__":
    main()
