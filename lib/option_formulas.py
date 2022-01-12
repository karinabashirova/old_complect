from lib.useful_things import *


def price_by_BS(S, K, T, sigma, option_type):
    if option_type == OptionType.call:
        return S * cdf(d1(S, K, T, sigma)) - K * cdf(d2(S, K, T, sigma))
    elif option_type == OptionType.put:
        return K * cdf(-d2(S, K, T, sigma)) - S * cdf(-d1(S, K, T, sigma))


def delta(S, K, T, sigma, option_type):
    if option_type == OptionType.call:
        return cdf(d1(S, K, T, sigma))
    else:
        return cdf(d1(S, K, T, sigma)) - 1


def gamma(S, K, T, sigma):
    return pdf(d1(S, K, T, sigma)) / (S * sigma * np.sqrt(T))


def theta(S, K, T, sigma):
    return -S * pdf(d1(S, K, T, sigma)) * sigma / (2 * np.sqrt(T))


def vega(S, K, T, sigma):
    return S * pdf(d1(S, K, T, sigma)) * np.sqrt(T)  # / 100


def charm(S, K, T, sigma):
    return -pdf(d1(S, K, T, sigma)) * (-d2(S, K, T, sigma) / (2 * T))


def d1(S, K, T, sigma):
    return (np.log(S / K) + (0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))


def d2(S, K, T, sigma):
    return d1(S, K, T, sigma) - sigma * np.sqrt(T)


def cdf(value):
    return stats.norm.cdf(value)


def pdf(value):
    return stats.norm.pdf(value)
