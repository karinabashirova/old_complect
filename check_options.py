import sys

import pandas as pd
import numpy as np
import argparse
import datetime
import warnings
import logging
from lib.option import Option
from lib import option_formulas as opt
from lib.surface_creation import surface_object_from_file

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None


class Portfolio:
    def __init__(self):
        self.sabr_object = None
        self.options = []

    def get_data_from_file(self, df_options, file_name, asset_spot):
        self.sabr_object = surface_object_from_file(file_name)

        print(df_options)

        for i in range(len(df_options)):
            try:
                self.options.append(
                    Option(self.sabr_object.today,
                           pd.to_datetime(df_options['maturity'].iloc[i], format='%Y-%m-%d %H:%M:%S'),
                           asset_spot, float(df_options['strike'].iloc[i]),
                           df_options['type'].iloc[i].upper(),
                           df_options['u_tkn'].iloc[i], df_options['f_tkn'].iloc[i]))
            except ValueError as e:
                print(e)
                logging.warning(f"Option was not created")

    def total_price(self, mult):
        price = np.zeros(len(self.options))
        volatility = np.zeros(len(self.options))
        print(len(self.options))

        for j, option in enumerate(self.options):
            strike = option.strike_price
            if mult != 1:
                strike = self.sabr_object.spot
            vol = self.sabr_object.interpolate_surface(option.time_before_expiration, strike)
            print(vol, strike, option.time_before_expiration)
            vol *= mult
            price[j] = option.price(vol)
            volatility[j] = vol
        print(price)
        print(volatility)
        return price, volatility

    def price_by_file(self, df_options, check_delta):
        price = []
        volatility = []

        for j, option in enumerate(self.options):
            if check_delta:
                p = df_options['price'].iloc[j] + (option.asset_price - df_options['ref_price'].iloc[j]) * \
                    df_options['delta'].iloc[j]

                if df_options['buy_sell'].iloc[j] == 'sell':
                    p = max(p, df_options['limit_price'].iloc[j])
                else:
                    p = min(p, df_options['limit_price'].iloc[j])
            else:
                p = df_options['price'].iloc[j]

            price.append(p)
            volatility.append(
                count_iv_from_price(option.asset_price, option.strike_price, option.time_before_expiration, p,
                                    option.option_type))

        return price, volatility


def read_df_options(options_file_name):
    try:
        df_options = pd.read_csv(options_file_name, header=None)
        columns = ['req', '0', 'f_tkn', 'u_tkn', 'type', 'strike', 'maturity', 'buy_sell', 'price', 'ref_price',
                   'delta', 'balance', 'limit_price']
        df_options.rename({i: columns[i] for i in range(len(columns))}, axis=1, inplace=True)

        if df_options.isna().sum().sum() > 0:
            logging.warning(f'Empty value in file {options_file_name}, row was dropped')

        df_options.dropna(inplace=True)
        df_options.reset_index(drop=True, inplace=True)

        return df_options

    except pd.errors.EmptyDataError:
        logging.error(f"File {options_file_name} is empty")
        sys.exit(1)

    except FileNotFoundError:
        logging.error(f"File {options_file_name} not exists")
        sys.exit(1)


def count_iv_from_price(spot, strike, time, real_price, option_type, eps=0.001, max_iterations=100):
    implied_volatility = 1
    dv = eps + 1

    iterations = 0

    while abs(dv) > eps and iterations <= max_iterations:
        theoretical_price = opt.price_by_BS(spot, strike, time, implied_volatility, option_type)
        dv = (float(theoretical_price) - float(real_price)) / opt.vega(spot, strike, time, implied_volatility)
        implied_volatility -= dv

        iterations += 1

    return implied_volatility  # if implied_volatility >= 0 else np.nan


def portfolio_main():
    logging.basicConfig(filename='option_greeks_error.log',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')

    parser = argparse.ArgumentParser(description='Volatility surface')
    parser.add_argument('surf', help='File with BTC surface')
    parser.add_argument('options', help='File with active options for unknown asset')
    parser.add_argument('cfg', help='File with difference in %')
    parser.add_argument('output', help='File for options output')
    parser.add_argument('sym', help='Asset symbol')
    parser.add_argument('spot', type=float, help='Asset spot')
    parser.add_argument('check', type=str, help='True in case check by delta, False in case simple price check')

    args = parser.parse_args()
    file_name = args.surf
    asset_spot = args.spot
    check_delta = args.check
    if check_delta == 'True':
        check_delta = True
        print(check_delta)
    else:
        check_delta = False

    cfg = pd.read_csv(args.cfg)
    max_strike_diff = cfg.strike_diff.values[0]
    max_vol_diff = cfg.vol_diff.values[0]

    df_options = read_df_options(args.options)
    df_options = df_options[df_options.u_tkn == args.sym]

    p = Portfolio()
    p.get_data_from_file(df_options, file_name, asset_spot)

    if args.sym not in ['BTC', 'ETH']:
        df_mult = pd.read_csv(f'vol_multipliers_{args.sym}.csv')
        mult = (df_mult['ask'].values[0] + df_mult['bid'].values[0]) / 2.
    else:
        mult = 1

    price0, volatility0 = p.total_price(mult)
    price1, volatility1 = p.price_by_file(df_options, check_delta)
    strikes = df_options['strike'].values
    strike_diff = [(p0 - p1) / k for p0, p1, k in zip(price0, price1, strikes)]
    vol_diff = [v1 - v0 for v0, v1 in zip(volatility0, volatility1)]

    df_options['BS_price'] = np.round(price0, 2)
    df_options['final_price'] = np.round(price1, 2)
    df_options['IV_by_BS_price'] = np.round(volatility0, 3)
    df_options['IV_by_final_price'] = np.round(volatility1, 3)
    df_options['IV_by_final_price'] = df_options['IV_by_final_price'].replace(np.nan, 0)
    df_options['strike_diff'] = np.round(strike_diff, 6)
    df_options['vol_diff'] = np.round(vol_diff, 6)
    print(df_options)
    df_options_bad = df_options[
        np.abs((df_options['strike_diff']) > max_strike_diff) | (np.abs(df_options['vol_diff']) > max_vol_diff) | (df_options['IV_by_final_price'] == 0)]
    df_options_good = df_options[
        np.abs((df_options['strike_diff']) <= max_strike_diff) & (np.abs(df_options['vol_diff']) <= max_vol_diff)]

    # print(df_options_bad)
    # print()
    # print(df_options_good)

    # df_options_bad.to_csv(args.output, index=False)
    df_options.to_csv(args.output, index=False)

    # df_greeks = pd.DataFrame({'time (UTC)': [datetime.datetime.utcnow()] * len(p.options),
    #                           'f_tkn': [o.founding_asset for o in p.options],
    #                           'u_tkn': [o.underlying_asset for o in p.options],
    #                           'type': [o.option_type for o in p.options],
    #                           'strike': [o.strike_price for o in p.options],
    #                           'maturity': [o.expiration_datetime for o in p.options],
    #                           'price': df_price_greeks.price,
    #                           'Delta': df_price_greeks.delta,
    #                           'Gamma': df_price_greeks.gamma,
    #                           'Vega': df_price_greeks.vega,
    #                           'Volatility': df_price_greeks.volatility})
    # try:
    #     df = pd.read_csv('option_calc_prices_greeks_' + ask_bid + '.csv')
    #     df_greeks.to_csv(r'option_calc_prices_greeks_' + ask_bid + '.csv', mode='a', index=False, header=False)
    # except FileNotFoundError:

    # df_greeks.to_csv(args.output, index=False)


if __name__ == '__main__':
    portfolio_main()
