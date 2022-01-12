import datetime
import sys
import time
import os
from make_volatility_surface import make_surface
from Naked.toolshed.shell import execute_js, muterun_js
from count_multipliers_for_vol import count_mult
from three_strikes import three_strikes_main
import argparse
import subprocess
import glob as gb
import json

parser = argparse.ArgumentParser(description='Get file with three BNB strikes')
parser.add_argument('spot', type=float, help='BNB spot')
parser.add_argument('expiration', type=str, help='BNB expiration')

args = parser.parse_args()

# print('BTC options table reading ---', end=' ')
#
# response = muterun_js(f'get_all_deribit_prices_mm_with_hats_v4.js 0 BTC >> option_table_BTC.csv')
#
# if response.exitcode == 0:
#     print('SUCCESS')
# else:
#     print('FAIL')
#     sys.exit(1)
#
# print('BTC surface making ---', end=' ')
# make_surface()
# print('SUCCESS')
#
# print('Multipliers counting ---', end=' ')
# count_mult()
# print('SUCCESS')

three_strikes_main(spot=args.spot, expiration=args.expiration + ' 08:00:00')

# path_to_scripts = \
#     r'C:\Users\admin\for python\HISTORY\get_1min_historical_spot_from_exchanges_'
#
# subprocess.run(path_to_scripts + '\Binance_SHP_OHLCV.exe')
