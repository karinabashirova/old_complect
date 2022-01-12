import sys

import pandas as pd
import numpy as np
from scipy import stats
import argparse
import datetime
import warnings
from scipy.interpolate import interp1d, interp2d
from lib.surface_creation import surface_object_from_file
import logging
from lib.option import Option
warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None


class Portfolio:
    def __init__(self):
        self.sabr_object = None
        self.options = []

    def get_data_from_file(self, df_options, file_name, asset_spot):
        self.sabr_object = surface_object_from_file(file_name)

        for i in range(len(df_options)):
            try:
                self.options.append(
                    Option(self.sabr_object.today,
                           pd.to_datetime(df_options['maturity'][i], format='%Y-%m-%d %H:%M:%S'),
                           asset_spot, float(df_options['strike'][i]),
                           df_options['type'][i].upper(),
                           df_options['u_tkn'][i], df_options['f_tkn'][i]))
            except ValueError:
                logging.warning(f"Option was not created")

    def total_price(self):
        delta = np.zeros(len(self.options))
        gamma = np.zeros(len(self.options))
        vega = np.zeros(len(self.options))
        price = np.zeros(len(self.options))

        for j, option in enumerate(self.options):
            vol = self.sabr_object.interpolate_surface(option.time_before_expiration, option.strike_price)

            delta[j] = option.delta(vol)
            gamma[j] = option.gamma(vol)
            vega[j] = option.vega(vol)
            price[j] = option.price(vol)

        return pd.DataFrame({'price': price, 'delta': delta, 'gamma': gamma, 'vega': vega / 100})


def read_df_options(options_file_name):
    try:
        df_options = pd.read_csv(options_file_name)

        if df_options.isna().sum().sum() > 0:
            logging.warning(f'Empty value in file {options_file_name}, row was dropped')

        df_options.dropna(inplace=True)
        df_options = df_options.reset_index(drop=True)

        if list(df_options.columns) != ['f_tkn', 'u_tkn', 'type', 'strike', 'maturity']:
            logging.error(f"Not enough columns in file {options_file_name}")
            sys.exit(1)

        if len(np.unique(df_options.f_tkn.values)) != 1:
            logging.error(f"Different founding tokens in file {options_file_name}")
            sys.exit(1)

        return df_options

    except pd.errors.EmptyDataError:
        logging.error(f"File {options_file_name} is empty")
        sys.exit(1)

    except FileNotFoundError:
        logging.error(f"File {options_file_name} not exists")
        sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(filename='option_greeks_error.log',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')

    parser = argparse.ArgumentParser(description='Options greeks')
    parser.add_argument('surf', help='File with BTC surface')
    parser.add_argument('options', help='File with active options for BTC')
    parser.add_argument('spot', type=float, help='BTC spot')
    parser.add_argument('output', help='File for options greeks')

    args = parser.parse_args()

    file_name = args.surf

    asset_spot = args.spot

    p = Portfolio()
    p.get_data_from_file(read_df_options(args.options), file_name, asset_spot)

    df_price_greeks = p.total_price()

    df_greeks = pd.DataFrame({'time (UTC)': [datetime.datetime.utcnow()]*len(p.options),
                              'f_tkn': [o.founding_asset for o in p.options],
                              'u_tkn': [o.underlying_asset for o in p.options],
                              'type': [o.option_type for o in p.options],
                              'strike': [o.strike_price for o in p.options],
                              'maturity': [o.expiration_datetime for o in p.options],
                              'price': df_price_greeks.price,
                              'Delta': df_price_greeks.delta,
                              'Gamma': df_price_greeks.gamma,
                              'Vega': df_price_greeks.vega})
    # try:
    #     df = pd.read_csv('option_calc_prices_greeks.csv')
    #     df_greeks.to_csv(r'option_calc_prices_greeks.csv', mode='a', index=False, header=False)
    # except FileNotFoundError:
    #     df_greeks.to_csv('option_calc_prices_greeks.csv', index=False)

    df_greeks.to_csv(args.output, index=False)
