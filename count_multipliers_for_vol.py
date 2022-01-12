from lib.useful_things import *
from lib.surface_creation import surface_object_from_file, surface_to_file
import lib.option_formulas as opt
from lib.option import get_years_before_expiration
import lib.plotter as pl
from lib.volatility import SABRSurface
import glob as gb


def count_volatility_multipliers(btc_df, asset_df, rolling_size, use_size):
    if use_size < rolling_size:
        print('error')
        quit()

    btc_vol = (np.log(btc_df / btc_df.shift(1)).ewm(span=24 * 60 * rolling_size).std()
               * np.sqrt(24 * 60 * 365)).spot[24 * 60 * use_size:]
    asset_vol = (np.log(asset_df / asset_df.shift(1)).ewm(span=24 * 60 * rolling_size).std()
                 * np.sqrt(24 * 60 * 365)).spot[24 * 60 * use_size:]

    volatility_ratio = asset_vol / btc_vol
    bid_multiplier = volatility_ratio.mean()
    ask_multiplier = bid_multiplier * np.quantile(volatility_ratio / bid_multiplier, 0.75)

    return bid_multiplier, ask_multiplier


def df_preparations(df_btc, df_asset):
    df_btc.fillna(method='bfill')
    df_asset.fillna(method='bfill')
    print()
    print(df_btc.datetime.values == df_asset.datetime.values)
    if (df_btc.datetime.values == df_asset.datetime.values):
        df_btc.set_index('datetime', inplace=True)
        df_asset.set_index('datetime', inplace=True)

        return df_btc, df_asset
    else:
        df = pd.merge(df_btc, df_asset, on='datetime', how='inner', suffixes=['_BTC', '_ASSET'])
        df.sort_values(by='datetime', inplace=True)

        df_btc = df[['datetime', 'spot_BTC']]
        df_btc.rename(columns={'spot_BTC': 'spot'}, inplace=True)
        df_btc.set_index('datetime', inplace=True)

        df_asset = df[['datetime', 'spot_ASSET']]
        df_asset.rename(columns={'spot_ASSET': 'spot'}, inplace=True)
        df_asset.set_index('datetime', inplace=True)
        print(df_btc.head())
        print(df_asset.head())
        return df_btc, df_asset


def count_mult(btc_file='BTCUSDT.csv', asset_file='BNBUSDT.csv', symbol='BNB'):
    rolling_size = 21
    use_size = 182

    btc_df = pd.read_csv(btc_file, header=None, usecols=[1, 2])
    btc_df.columns = ['datetime', 'spot']
    # btc_df['datetime'] = [datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S') for d in btc_df['datetime']]
    btc_df['datetime'] = [datetime.datetime.strptime(d, '%Y-%b-%d %H:%M:%S') for d in btc_df['datetime']]

    asset_df = pd.read_csv(asset_file, header=None, usecols=[1, 2])
    asset_df.columns = ['datetime', 'spot']
    # asset_df['datetime'] = [datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S') for d in asset_df['datetime']]
    asset_df['datetime'] = [datetime.datetime.strptime(d, '%Y-%b-%d %H:%M:%S') for d in asset_df['datetime']]
    # asset_df = asset_df[::-1]

    btc_df, asset_df = df_preparations(btc_df, asset_df)

    b, a = count_volatility_multipliers(btc_df, asset_df, rolling_size, use_size)

    pd.DataFrame({'bid': [b], 'ask': [a]}).to_csv(f'vol_multipliers_{symbol}.csv', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Volatility surface')
    parser.add_argument('btc', help='File with history of BTC spot')
    parser.add_argument('asset', help='File with history of another asset spot')
    parser.add_argument('sym', help='Asset symbol')

    args = parser.parse_args()

    btc_file = args.btc
    asset_file = args.asset
    symbol = args.sym

    count_mult(btc_file, asset_file, symbol)
