import os

from lib.useful_things import *
from lib.volatility import IVSurface, SABRSurface
from lib.forward import ForwardPriceCounter
import lib.option_formulas as opt
from lib.exchange_data_reader import ExchangeDataReader
from lib.last_table_reader import LastTableReader
from lib.option import get_years_before_expiration


def get_data(file_name, call_put_diff, N1, N2, read_row, step):
    reader = LastTableReader(file_name)
    reader.get_data_from_file(call_put_diff, N1, N2)

    k = -1

    today = reader.today[k]
    spot = reader.spot[k]
    dates = [date for date in reader.expiration_dates[k] if date != 'nan']
    times = [time for time in reader.time_before_expiration[k] if not np.isnan(time)]

    different_strikes_price = dict()
    different_strikes_price['ask_c'] = [price for price in reader.price['ask_c'][k] if price != [np.nan]]
    different_strikes_price['ask_p'] = [price for price in reader.price['ask_p'][k] if price != [np.nan]]
    different_strikes_price['bid_c'] = [price for price in reader.price['bid_c'][k] if price != [np.nan]]
    different_strikes_price['bid_p'] = [price for price in reader.price['bid_p'][k] if price != [np.nan]]

    strikes = [list(np.array(strikes)) for strikes in reader.strikes[k] if strikes != [np.nan]]

    all_strikes = np.unique(np.hstack(strikes))

    prices = {key: np.full((len(times), len(all_strikes)), np.nan) for key in keys}

    for key in keys:
        for n in range(len(times)):
            for m in range(len(strikes[n])):
                index = np.where(all_strikes == strikes[n][m])[0][0]
                prices[key][n][index] = different_strikes_price[key][n][m]

    return Data(all_strikes, times, dates, prices, spot, today)


def get_data_by_reader(reader, k):
    today = reader.today[k]
    spot = reader.spot[k]
    dates = [date for date in reader.expiration_dates[k] if date != 'nan']
    times = [time for time in reader.time_before_expiration[k] if not np.isnan(time)]

    different_strikes_price = dict()
    different_strikes_price['ask_c'] = [price for price in reader.price['ask_c'][k] if price != [np.nan]]
    different_strikes_price['ask_p'] = [price for price in reader.price['ask_p'][k] if price != [np.nan]]
    different_strikes_price['bid_c'] = [price for price in reader.price['bid_c'][k] if price != [np.nan]]
    different_strikes_price['bid_p'] = [price for price in reader.price['bid_p'][k] if price != [np.nan]]

    strikes = [list(np.array(strikes)) for strikes in reader.strikes[k] if strikes != [np.nan]]

    all_strikes = np.unique(np.hstack(strikes))

    prices = {key: np.full((len(times), len(all_strikes)), np.nan) for key in keys}

    for key in keys:
        for n in range(len(times)):
            for m in range(len(strikes[n])):
                index = np.where(all_strikes == strikes[n][m])[0][0]
                prices[key][n][index] = different_strikes_price[key][n][m]

    return Data(all_strikes, times, dates, prices, spot, today)


def get_surface(data, cut=False, use_weights=False):
    strikes = data.strikes
    times = data.times
    dates = data.dates
    prices = data.prices
    spot = data.spot
    today = data.today

    iv_by_spot = {key: IVSurface(times, dates, today, [spot] * len(times), strikes, spot, prices[key], key) for key in
                  keys}

    forward_counter = ForwardPriceCounter(spot, times, strikes, prices)
    forward, f = forward_counter.count_average_forward(iv_by_spot)

    # print(times, dates, today, [spot] * len(times), strikes, spot)
    # print('forward, f:', forward, f)

    for k in range(len(f)):
        if len(f[k]) < len(times):
            f[k] = [spot] * len(times)

    iv_by_forward = {key: IVSurface(times, dates, today, f[k], strikes, spot, prices[key], key) for k, key in
                     enumerate(keys)}

    # ?????????????? ???????????? ??????????????
    sum_surface = np.zeros_like(iv_by_forward['ask_c'].surface)
    for key in keys:
        sum_surface = np.nansum(np.dstack((sum_surface, iv_by_forward[key].surface)), 2)

    indices = np.arange(len(strikes))[np.sum(sum_surface, axis=0) == 0]

    strikes = np.delete(strikes, indices)
    for key in keys:
        iv_by_forward[key].strike_prices = np.delete(iv_by_forward[key].strike_prices, indices)
        iv_by_forward[key].surface = np.delete(iv_by_forward[key].surface, indices, axis=1)
        iv_by_forward[key].delta = np.delete(iv_by_forward[key].delta, indices, axis=1)

    # ?????????????? ???????????? ????????????????????
    sum_surface = np.zeros_like(iv_by_forward['ask_c'].surface)
    for key in keys:
        sum_surface = np.nansum(np.dstack((sum_surface, iv_by_forward[key].surface)), 2)

    indices = np.arange(len(times))[np.sum(sum_surface, axis=1) == 0]

    times = np.delete(times, indices)
    dates = np.delete(dates, indices)
    forward = np.delete(forward, indices)
    for key in keys:
        iv_by_forward[key].times_before_expiration = np.delete(iv_by_forward[key].times_before_expiration, indices)
        iv_by_forward[key].expiration_dates = np.delete(iv_by_forward[key].expiration_dates, indices)
        iv_by_forward[key].asset_prices = np.delete(iv_by_forward[key].asset_prices, indices)
        iv_by_forward[key].real_option_prices = np.delete(iv_by_forward[key].real_option_prices, indices, axis=0)
        iv_by_forward[key].surface = np.delete(iv_by_forward[key].surface, indices, axis=0)
        iv_by_forward[key].delta = np.delete(iv_by_forward[key].delta, indices, axis=0)

    delta = {key: np.full((len(times), len(strikes)), np.nan) for key in keys}

    for key in keys:
        for n, time in enumerate(times):
            for m, strike in enumerate(strikes):
                delta[key][n][m] = opt.delta(forward[n],
                                             strike,
                                             time,
                                             iv_by_forward[key].surface[n][m],
                                             iv_by_forward[key].options_type)

    sabr_obj = SABRSurface(times, dates, today, forward, strikes, spot)
    sabr_obj.evaluate(iv_by_forward, delta, use_weights, cut)
    # if np.max(sabr_obj.surface) > 5 * np.min(sabr_obj.surface):
    sabr_obj, iv_by_forward = cut_dates_by_vol_size(data, sabr_obj, iv_by_forward)

    return sabr_obj, iv_by_forward


def cut_dates_by_vol_size(data, sabr_obj, iv_by_forward):
    indices = []
    for n in range(len(sabr_obj.times_before_expiration)):
        if (
                # np.max(sabr_obj.surface[n]) > 5 * np.min(sabr_obj.surface[n]) and
                (sabr_obj.delta['surface_c'][n].min() > 0.5 or sabr_obj.delta['surface_c'][n].max() < 0.5
                 or np.any(np.diff(sabr_obj.delta['surface_c'][n]) > 0))
        ):
            indices.append(n)
    # pprint(f'indices {indices}', 'c')

    sabr_obj.times_before_expiration = np.delete(sabr_obj.times_before_expiration, indices)
    sabr_obj.expiration_dates = np.delete(sabr_obj.expiration_dates, indices)
    sabr_obj.asset_prices = np.delete(sabr_obj.asset_prices, indices)
    sabr_obj.surface = np.delete(sabr_obj.surface, indices, axis=0)
    sabr_obj.delta['surface_c'] = np.delete(sabr_obj.delta['surface_c'], indices, axis=0)
    sabr_obj.delta['surface_p'] = np.delete(sabr_obj.delta['surface_p'], indices, axis=0)

    for key in keys:
        iv_by_forward[key].times_before_expiration = np.delete(iv_by_forward[key].times_before_expiration, indices)
        iv_by_forward[key].expiration_dates = np.delete(iv_by_forward[key].expiration_dates, indices)
        iv_by_forward[key].asset_prices = np.delete(iv_by_forward[key].asset_prices, indices)
        iv_by_forward[key].real_option_prices = np.delete(iv_by_forward[key].real_option_prices, indices, axis=0)
        iv_by_forward[key].surface = np.delete(iv_by_forward[key].surface, indices, axis=0)
        iv_by_forward[key].delta = np.delete(iv_by_forward[key].delta, indices, axis=0)

    return sabr_obj, iv_by_forward


def surface_to_file(surface_object, file_name):
    with open(r"./" + file_name, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["options_request_time", str(surface_object.today)])

    df = pd.DataFrame({'strike': surface_object.strike_prices})
    df = df.set_index('strike')

    for n, date in enumerate(surface_object.expiration_dates):
        df[str(pd.to_datetime(date, format='%Y-%m-%d %H:%M:%S'))] = surface_object.surface[n]

    df.to_csv(file_name, mode='a')

    prefix = 'data_for_'
    extra_file_name = prefix + file_name[:-4] + '.txt'

    with open(extra_file_name, 'a') as f:
        f.write('\n' + str({'options_request_time': surface_object.today,
                            'spot': surface_object.spot,
                            'forward': list(surface_object.asset_prices)}))

    pd.DataFrame(surface_object.params).to_csv('sabr_params.csv', index=False)


def surface_object_from_file(file_name):
    try:
        num = 0
        with open(file_name) as file:
            for i, row in enumerate(file):
                tmp = row.strip().split(',')

                if tmp[0] == 'strike':
                    num = i

        with open(file_name) as file:
            content = file.readlines()
            surface_request_time = datetime.datetime.strptime(content[num - 1].strip().split(',')[1], '%Y-%m-%d %H:%M:%S')

        df_vol = pd.read_csv(file_name, skiprows=num)

        df_vol = df_vol.reset_index(drop=True)
        df_vol = df_vol.astype('float')

        dates = [datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S') for date in df_vol.columns[1:]]
        strikes = df_vol['strike'].values
        surface = df_vol[df_vol.columns[1:]].values.T

        prefix = 'data_for_'
        extra_file_name = prefix + file_name[:-4] + '.txt'

        if not os.path.exists(extra_file_name):
            print(f'Check the file with surface spot and forwards. File with surface spot and forward "{extra_file_name}" is not found')
            sys.exit(2)

        with open(extra_file_name, 'r') as file:
            last_string_in_config = list(file)[-1]

        data = eval(last_string_in_config)

        today = data['options_request_time']
        spot = data['spot']
        forward = data['forward']

        if today != surface_request_time:
            print(f"Check the file with surface spot and forwards. Request time in {file_name} doesn't match request time in {extra_file_name}")
            sys.exit(2)

        if len(forward) != len(dates):
            print(f"Check the file with surface spot and forwards. Number of expirations in {file_name} doesn't match number of forwards in {extra_file_name}")
            sys.exit(2)

        times = [get_years_before_expiration(today, date) for date in dates]

        delta = {'surface_c': np.full((len(times), len(strikes)), np.nan),
                 'surface_p': np.full((len(times), len(strikes)), np.nan)}

        for n, time in enumerate(times):
            for m, strike in enumerate(strikes):
                delta['surface_c'][n][m] = opt.delta(forward[n], strike, time, surface[n][m], OptionType.call)
                delta['surface_p'][n][m] = opt.delta(forward[n], strike, time, surface[n][m], OptionType.put)

        return SABRSurface(times, dates, today, forward, strikes, spot, surface, delta)
        # return dates, times, strikes, surface, delta, today, spot, forward

    except FileNotFoundError:
        raise Exception(f'File {file_name} not found')
