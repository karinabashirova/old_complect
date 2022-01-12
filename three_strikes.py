import csv
import sys

import pandas as pd
import numpy as np
import argparse
import datetime
import warnings
import logging
from lib.option import get_years_before_expiration
from lib.surface_creation import surface_object_from_file
from lib import option_formulas
from lib.useful_things import OptionType

warnings.filterwarnings("ignore")
pd.options.mode.chained_assignment = None


def count_strikes_from_delta(sabr_object, mult, spot, delta=None, time=None):
    if delta is None and time is None:
        delta = sabr_object.delta['surface_c'][0]
        time = sabr_object.times_before_expiration[0]

    elif delta is None and time is not None:
        delta = sabr_object.delta_slice_for_new_time(time)

    elif delta is not None and time is None:
        sys.exit(1)

    asset_strikes = np.zeros_like(delta)
    asset_delta = np.zeros_like(delta)
    print('4*spot', 4 * spot)
    for n, real_delta in enumerate(delta):
        prev_error = 1e6

        vol = mult * sabr_object.get_vol_by_time_delta(time, 0.5)

        for strike in np.arange(10, 4 * spot, 1):
            d = option_formulas.delta(spot, strike, time, vol, OptionType.call)
            error = abs(1 - d / real_delta)

            if error < prev_error:
                asset_delta[n] = d
                asset_strikes[n] = strike
                prev_error = error
            # print(strike, error)
    print(asset_strikes)
    return asset_strikes


def three_strikes_main(spot, expiration, file_name='vol_surface_BTC.csv', symbol='BNB'):
    logging.basicConfig(filename='option_greeks_error.log',
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')

    # t = datetime.datetime.utcnow()
    # friday = t + datetime.timedelta((4 - t.weekday()) % 7)
    # expiration = friday - datetime.timedelta(hours=friday.hour, minutes=friday.minute, seconds=friday.second,
    #                                              microseconds=friday.microsecond) + datetime.timedelta(hours=8)
    # if expiration < t:
    #     expiration += datetime.timedelta(days=7)

    expiration = datetime.datetime.strptime(expiration, '%Y-%m-%d %H:%M:%S')
    print(expiration)
    # print()
    df_mult = pd.read_csv(f'vol_multipliers_{symbol}.csv')
    asset_spot = spot

    sabr_object = surface_object_from_file(file_name)
    time = get_years_before_expiration(datetime.datetime.utcnow(), expiration)

    with open('three_strikes_' + symbol + '.csv', "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Request", str(datetime.datetime.utcnow()), 'Expiration', expiration])
    # delta_list = [-0.1, -0.2, -0.3]
    delta_list = [0.25, 0.5, 0.75]
    # delta_list = [-0.25, -0.5, -0.75]
    # delta_list = [-0.9, -0.8, -0.7]
    # delta_list = [0.9, 0.8, 0.7]
    print(delta_list)
    df = pd.DataFrame({'delta': delta_list, 'ask': np.full(3, np.nan), 'bid': np.full(3, np.nan)})

    for ask_bid in ['ask', 'bid']:
        mult = df_mult[ask_bid].values[0]

        df[ask_bid] = count_strikes_from_delta(sabr_object,
                                               mult=mult, spot=asset_spot, delta=delta_list, time=time)

    df.to_csv('three_strikes_' + symbol + '.csv', mode='a', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Volatility surface')
    parser.add_argument('surf', help='File with BTC surface')
    parser.add_argument('sym', type=str, help='Unknown asset symbol')
    parser.add_argument('spot', type=float, help='Unknown asset spot')
    parser.add_argument('expiration', type=str, help='Unknown asset expiration')

    args = parser.parse_args()
    file_name = args.surf
    symbol = args.sym
    spot = args.spot
    exp = args.expiration

    three_strikes_main(spot, exp, file_name, symbol)
