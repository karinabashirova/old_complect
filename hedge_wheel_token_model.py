import csv
from datetime import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
import warnings
import datetime
import copy
from scipy import stats
import pwlf
import time
from sklearn.linear_model import LinearRegression
from GPyOpt.methods import BayesianOptimization
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# warnings.filterwarnings("ignore")
# pd.options.mode.chained_assignment = None

from lib.exchange_data_reader_historical_new_format import HistoricalReaderNewFormat
from lib.exchange_data_reader_historical import HistoricalReader
# from lib.forward_price_counter import ForwardPriceCounter
# from lib.volatility_surface import Volatility
from lib.option import Option

from lib.useful_things import *
from lib.surface_creation import surface_object_from_file, surface_to_file
import lib.option_formulas as opt
from lib.option import get_years_before_expiration
import lib.plotter as pl
from lib.volatility import get_strike_by_delta, delta_slice_for_new_time, interpolate_surface
from lib.surface_creation import get_data_by_reader, get_surface


class Portfolio:
    def __init__(self, reader, expiration, today, spot, option_type, btc_count, usd_count):
        self.reader = reader

        index = np.where(np.array(self.reader.today) == today)[0][0]
        self.data = get_data_by_reader(reader, index)

        vol, _ = get_surface(self.data)

        time = get_years_before_expiration(today, expiration)

        strike_c, strike_p = 1.05 * spot, 0.95 * spot  # get_strike_for_one_request_time(vol, time)
        print(f'strike_c {strike_c}, strike_p {strike_p}')
        self.options_long = []

        if option_type == 'call':
            self.options_short = [
                Option(today, expiration, spot, strike_c, OptionType.call)]
            self.vol_short = [
                interpolate_surface(vol.surface, vol.times_before_expiration, vol.strike_prices, time,
                                    self.options_short[0].strike_price)]
        else:
            self.options_short = [
                Option(today, expiration, spot, strike_p, OptionType.put)]
            self.vol_short = [
                interpolate_surface(vol.surface, vol.times_before_expiration, vol.strike_prices, time,
                                    self.options_short[0].strike_price)]
        self.vol_long = []

    def update_options(self, today, spot):
        index = np.where(np.array(self.reader.today) == today)[0][0]
        self.data = get_data_by_reader(self.reader, index)

        vol, _ = get_surface(self.data)
        surface_to_file(vol, 'vol' + str(today)[:10] + '_' + str(today)[11:13] + '.csv')

        print(f'vol strike len {len(vol.strike_prices)}, vol time len {len(vol.times_before_expiration)}')

        # for i, option in enumerate(self.options_long):
        #     option.current_datetime = today
        #     option.asset_price = spot
        #
        #     self.vol_long[i] = interpolate_surface(vol.surface,
        #                                            vol.times_before_expiration,
        #                                            vol.strike_prices,
        #                                            option.time_before_expiration,
        #                                            option.strike_price)

        for i, option in enumerate(self.options_short):
            option.current_datetime = today
            option.asset_price = spot

            print(f'option strike {option.strike_price}, option date {option.current_datetime}')

            self.vol_short[i] = interpolate_surface(vol.surface,
                                                    vol.times_before_expiration,
                                                    vol.strike_prices,
                                                    option.time_before_expiration,
                                                    option.strike_price)

    @property
    def returns_from_options(self):
        returns_from_options = 0

        for i, option_long in enumerate(np.array(self.options_long)):
            if option_long.option_type == OptionType.call:
                returns_from_options += max(0, option_long.asset_price - option_long.strike_price)
            if option_long.option_type == OptionType.put:
                returns_from_options += max(0, -option_long.asset_price + option_long.strike_price)

        for i, option_short in enumerate(np.array(self.options_short)):
            if option_short.option_type == OptionType.call:
                returns_from_options -= max(0, option_short.asset_price - option_short.strike_price)
            if option_short.option_type == OptionType.put:
                returns_from_options -= max(0, -option_short.asset_price + option_short.strike_price)

        return returns_from_options


# def hedge(p, today_list, spot_list):
#     print('hedge()')
#
#     price_by_hedge = 0
#     price_by_BS = 0
#
#     C0, P0 = 0, 0
#
#     for i, option_long in enumerate(p.options_long):
#         C0 += option_long.price(p.vol_long[i])
#
#     for i, option_short in enumerate(p.options_short):
#         P0 += option_short.price(p.vol_short[i])
#
#     real_price = 0
#     for j in range(1, len(spot_list)):
#         t = today_list[j]
#         s = spot_list[j]
#
#         print(f'\tRequest time [{j}] {t}')
#
#         delta0 = 0
#
#         for i, option_long in enumerate(p.options_long):
#             delta0 += option_long.delta(p.vol_long[i])
#
#         for i, option_short in enumerate(p.options_short):
#             delta0 += option_short.delta(p.vol_short[i])
#
#         for o in p.options_long + p.options_short:
#             print('\t', o)
#
#         p.update_options(t, s)
#
#         C1, P1 = 0, 0
#
#         for i, option_long in enumerate(p.options_long):
#             C1 = np.nansum([option_long.price(p.vol_long[i]), C1])
#
#         for i, option_short in enumerate(p.options_short):
#             P1 = np.nansum([option_short.price(p.vol_short[i]), P1])
#
#         option_part = (C1 - C0) + (P1 - P0)
#
#         price_by_BS = np.nansum([option_part, price_by_BS])
#
#         # print('\tspot[i]', s, 'spot[i-1]', spot_list[j - 1], 'today', t)
#         # print('\t(C1 - C0)', (C1 - C0), '(P1 - P0)', (P1 - P0))
#         print(f'\toption_part: {option_part}, hedging_part: {hedging_part}, opt-hedg: {option_part - hedging_part}')
#         print()
#
#         C0, P0 = C1, P1
#         if j == 0:
#             real_price = C1
#
#     return price_by_BS - price_by_hedge, real_price


def get_strike_for_one_request_time(sabr, time):
    new_delta_c = delta_slice_for_new_time(sabr.times_before_expiration, sabr.strike_prices, sabr.delta['surface_c'],
                                           time)
    new_delta_p = delta_slice_for_new_time(sabr.times_before_expiration, sabr.strike_prices, sabr.delta['surface_p'],
                                           time)

    strike_c = get_strike_by_delta(sabr.strike_prices, new_delta_c, 0.25)
    strike_p = get_strike_by_delta(sabr.strike_prices, new_delta_p, -0.25)
    return strike_c, strike_p


def get_vol_from_surface(option, reader, today):
    index = np.where(np.array(reader.today) == today)[0][0]
    data = get_data_by_reader(reader, index)

    vol, points = get_surface(data)
    # print(f'MAXVOL {np.max(vol.surface)}')
    # pl.plot_surface(vol, points)
    # surface_to_file(vol, 'vol' + str(today)[:10] + '_' + str(today)[11:13] + '.csv')

    vol_short = interpolate_surface(vol.surface,
                                    vol.times_before_expiration,
                                    vol.strike_prices,
                                    option.time_before_expiration,
                                    option.strike_price)
    return vol_short


def main():
    call_put_diff = 0.1
    N1, N2 = 0, 30
    # read_row, step = 'first', 1
    # read_row, step = 'last', 1
    read_row, step = 'all', 60

    cut = True
    use_weights = True

    file_path = 'C:\\Users\\admin\\for python\\Surface for unknown asset with the very good lib\\complect\\btc_options\\'

    reader_btc = HistoricalReaderNewFormat(file_path)
    # reader_btc = HistoricalReader(file_path + 'OptBestBA_1m_Deribit_BTC_USDT_20210527.csv')
    reader_btc.get_data_from_file(call_put_diff, N1, N2, read_row, step)

    reader = reader_btc

    spot_list = reader_btc.spot

    start_n = 0
    # zero_date = datetime.datetime.strptime('2021-05-27 09:58:00', '%Y-%m-%d %H:%M:%S')
    zero_date = reader.today[0]
    # datetime.datetime.strptime('2021-02-05 08:00:00', '%Y-%m-%d %H:%M:%S')  # reader.today[start_n*24]
    k0 = np.where(np.array(reader.today) == zero_date)[0][0]

    sum_hedge_result = 0
    sum_intrinsic_value = 0

    # list_hedge_result = []
    # list_intrinsic_value = []
    list_datetime = []
    list_usd_price = []
    list_btc_price = []

    btc = 1
    usd = 0

    for n in range(start_n, 17):
        k = k0 + n * 24

        today = reader.today[k]
        spot = reader.spot[k]
        expiration = reader.today[k] + timedelta(hours=24)

        print('--------------------------------' + '-' * 30)
        print(f'[{n}, {k}]: {today} {expiration}')

        if n == start_n:
            option = Option(today, expiration, spot, spot * 1.01, OptionType.call)
            vol = get_vol_from_surface(option, reader, today)
            usd = option.price(vol)
        else:
            print(f'BEFORE: btc {btc}, usd {usd}')
            print('     ', option)

            if option.option_type == 'CALL' and option.strike_price < spot:
                usd += option.strike_price * btc
                btc = 0
                option = Option(today, expiration, spot, spot * 0.99, OptionType.put)
                vol = get_vol_from_surface(option, reader, today)
                usd += option.price(vol) * usd / option.strike_price
                # print('Продали все BTC => получили $')

            elif option.option_type == 'CALL' and option.strike_price >= spot:
                option = Option(today, expiration, spot, spot * 1.01, OptionType.call)
                vol = get_vol_from_surface(option, reader, today)
                usd += option.price(vol) * btc
                if usd < 1e-5:
                    print('*'*10, usd, option.price(vol), btc)
                # print('Продали колл => получили $')

            elif option.option_type == 'PUT' and option.strike_price > spot:
                btc += usd / option.strike_price
                usd = 0
                option = Option(today, expiration, spot, spot * 1.01, OptionType.call)
                vol = get_vol_from_surface(option, reader, today)
                usd += option.price(vol) * btc
                if usd < 1e-5:
                    print('*'*10, usd, option.price(vol), btc)
                # print('Купили BTC за все $, Продали колл => получили $')

            elif option.option_type == 'PUT' and option.strike_price <= spot:
                option = Option(today, expiration, spot, spot * 0.99, OptionType.put)
                vol = get_vol_from_surface(option, reader, today)
                usd += option.price(vol) * usd / option.strike_price
                # print('Продали put => получили $')

            print(f'AFTER: btc {btc}, usd {usd}, vol {vol}')
            print('      ', option)

        list_btc_price.append(btc)
        list_usd_price.append(usd)
        list_datetime.append(today)

        # try:
        #     if n == start_n:
        #         option_type = 'call'
        #         btc_count = 1
        #     elif list_intrinsic_value[-1] != 0:
        #         option_type = 'call'
        #         btc_count -= 1
        #     else:
        #         option_type = 'put'
        #         btc_count += 1
        #
        #     p = Portfolio(reader, expiration, today, spot_list[k], option_type, btc_count, 0)
        #
        #     real_price = p.options_short[0].price(p.vol_short[i]), ) #hedge(p, reader.today[k:k + 24], spot_list[k:k + 24])
        #     intrinsic_value = p.returns_from_options
        #
        #     # sum_hedge_result += hedge_result
        #     # sum_intrinsic_value += intrinsic_value
        #
        #     list_datetime.append(today)
        #     list_hedge_result.append(hedge_result)
        #     list_intrinsic_value.append(intrinsic_value)
        #     list_price.append(real_price)

        # res_cumulative.append(sum_hedge_result + sum_intrinsic_value)

        # except ValueError as e:
        #     print('ValueError')
        #     if hasattr(e, 'message'):
        #         print(e.message)
        #     else:
        #         print(e)
        #     break
        #
        # except IndexError as e:
        #     print('IndexError')
        #     if hasattr(e, 'message'):
        #         print(e.message)
        #     else:
        #         print(e)
        #     break

    df = pd.DataFrame()

    df['Datetime'] = list_datetime
    df['USD'] = np.round(list_usd_price, 3)
    df['BTC'] = np.round(list_btc_price, 3)

    df.to_csv('wheel_result.csv', index=False)
    # df.to_csv('hedge_result_reversal_two_portfolios2.csv', index=False)
    print(df)


if __name__ == '__main__':
    main()
