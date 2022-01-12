import sys

import pandas as pd
import numpy as np
import argparse
import datetime
import warnings
import logging
from lib.option import Option, get_years_before_expiration
from lib.surface_creation import surface_object_from_file

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None


class Portfolio:
    def __init__(self):
        self.sabr_object = None
        self.options = []
        self.balance = []

    def get_data_from_file(self, df_options, file_name, asset_spot):
        self.sabr_object = surface_object_from_file(file_name)

        for i in range(len(df_options)):
            try:
                self.options.append(
                    Option(self.sabr_object.today,
                           df_options['maturity'].iloc[i],
                           asset_spot, float(df_options['strike'].iloc[i]),
                           df_options['type'].iloc[i].upper(),
                           df_options['u_tkn'].iloc[i], df_options['f_tkn'].iloc[i]))
                self.balance.append(df_options['first'].iloc[i] - df_options['second'].iloc[i])
            except ValueError as e:
                print(f"Option was not created")
                print(e)

    def total_price(self, mult):
        delta = np.zeros(len(self.options))
        gamma = np.zeros(len(self.options))
        vega = np.zeros(len(self.options))
        price = np.zeros(len(self.options))

        for j, option in enumerate(self.options):
            if mult == 1:
                vol = mult * self.sabr_object.interpolate_surface(option.time_before_expiration, option.strike_price)
            else:
                strike = self.sabr_object.spot
                vol = mult * self.sabr_object.interpolate_surface(option.time_before_expiration, strike)

            delta[j] = option.delta(vol) * self.balance[j]
            gamma[j] = option.gamma(vol) * self.balance[j]
            vega[j] = option.vega(vol) * self.balance[j]
            price[j] = option.price(vol) * self.balance[j]

        return pd.DataFrame({'price': price, 'delta': delta, 'gamma': gamma, 'vega': vega / 100})


def df_preparation(file_name, tkn_name):
    df = pd.read_csv(file_name, header=None)

    df.columns = ['q', 'f_tkn', 'u_tkn', 'type', 'strike', 'maturity', 'first', 'second', 'third',
                  'forth', 'check']

    df = df[df.u_tkn == tkn_name]
    df = df[df.q == df['q'].iloc[-1]]
    df = df[df.f_tkn != 'error']

    df.reset_index(drop=True)
    df.maturity = [datetime.datetime.strptime(d, '%Y-%b-%d') + datetime.timedelta(hours=8) for d in df.maturity]
    df.q = [datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S') for d in df.q]

    try:
        df['time_before_expiration'] = [get_years_before_expiration(df.q.iloc[i], df.maturity.iloc[i]) for i in
                                        range(len(df))]
    except ValueError as e:
        print(e)
        sys.exit(2)

    return df


if __name__ == '__main__':
    logging.basicConfig(filename='option_greeks_error.log',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')

    parser = argparse.ArgumentParser(description='Greeks for asset with balances')
    parser.add_argument('surf', help='File with asset surface')
    parser.add_argument('balances', help='File with options')
    parser.add_argument('sym', type=str, help='Asset symbol')
    parser.add_argument('spot', type=float, help='Asset spot')
    parser.add_argument('output', help='File for options greeks')
    # parser.add_argument('expiration', type=str, help='Unknown asset spot')

    args = parser.parse_args()

    if args.sym not in ['BTC', 'ETH']:
        df_mult = pd.read_csv(f'vol_multipliers_{args.sym}.csv')
        mult = (df_mult['ask'].values[0] + df_mult['bid'].values[0]) / 2.
    else:
        mult = 1

    p = Portfolio()
    df = df_preparation(args.balances, args.sym)
    p.get_data_from_file(df, args.surf, args.spot)

    df_price_greeks = p.total_price(mult)

    df_result = pd.DataFrame({'time (UTC)': [datetime.datetime.utcnow()],
                              'f_tkn': [p.options[0].founding_asset],
                              'u_tkn': [p.options[0].underlying_asset],
                              'total_value': [df_price_greeks.sum().price],
                              'Delta': [df_price_greeks.sum().delta],
                              'Gamma': [df_price_greeks.sum().gamma],
                              'Vega': [df_price_greeks.sum().vega]})

    df_result.to_csv(args.output, index=False)

