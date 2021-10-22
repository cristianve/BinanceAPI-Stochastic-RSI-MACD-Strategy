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

    df = getDataFrameFromAPI('ADAUSDT',Client.KLINE_INTERVAL_1DAY, '1 year ago UTC')



    # Apply RSI MCAD K-D Technics
    applytechnicals(df)

    # Update decision
    inst = Signals(df, 5)  # lags very important parameter 2, 3 or 5
    inst.decide()

    #when trigger / buy == 1


    print(df)

if __name__ == "__main__":
    main()
