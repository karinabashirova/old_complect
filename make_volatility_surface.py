from lib.surface_creation import *
import lib.plotter as pl


def make_surface(file_name='option_table_BTC.csv', surface_file_name='vol_surface_BTC.csv', plot_surface='n'):
    read_row = 'last'  # , 'all'   'first'
    step = 1
    call_put_diff = 0.1
    N1, N2 = 0, 10000

    cut, use_weights = True, False

    data = get_data(file_name, call_put_diff, N1, N2, read_row, step)
    sabr, iv = get_surface(data, cut, use_weights)

    surface_to_file(sabr, surface_file_name)

    if plot_surface == 'y':
        pl.plot_surface(sabr, iv)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Volatility surface')
    parser.add_argument('f', help='File name with options prices (data from deribit)')
    parser.add_argument('n', help='File name for surface')
    parser.add_argument('--p', default='n', type=str, help='Plot surface "y"/"n"')

    args = parser.parse_args()

    file_name = args.f
    surface_file_name = args.n
    plot_surface = args.p

    make_surface(file_name, surface_file_name, plot_surface)
