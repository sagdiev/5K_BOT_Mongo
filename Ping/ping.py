from pymongo import MongoClient
from poloniex import Poloniex
from binance.client import Client
from bittrex.bittrex import *
import krakenex
import telebot
import Ping.constants as constants_ping
# import time
# import math as m
# import datetime
# import sys
# import os
# import psutil
# from subprocess import Popen, PIPE
# import signal

api_key_polo_ping = constants_ping.api_key_polo_ping
api_secret_polo_ping = constants_ping.api_secret_polo_ping
polo = Poloniex(api_key_polo_ping, api_secret_polo_ping)

api_key_binance_ping = constants_ping.api_key_binance_ping
api_secret_binance_ping = constants_ping.api_secret_binance_ping
client = Client(api_key_binance_ping, api_secret_binance_ping)

api_key_kraken_ping = constants_ping.api_key_kraken_ping
api_secret_kraken_ping = constants_ping.api_secret_kraken_ping
kraken = krakenex.API(key=api_key_kraken_ping, secret=api_secret_kraken_ping)

api_key_bittrex_ping = constants_ping.api_key_bittrex_ping
api_secret_bittrex_ping = constants_ping.api_secret_bittrex_ping
my_bittrex = Bittrex(api_key_bittrex_ping, api_secret_bittrex_ping, api_version=API_V1_1)

token = constants_ping.token
tele_bot = telebot.TeleBot(token)
set_id = constants_ping.set_id

client_mongo = MongoClient('127.0.0.1', 27017)

# підєднатися до бази і колекції
db = client_mongo.DB_bigbott
DB_market_collection = db.DB_market
DB_bot_collection = db.DB_bot
DB_log_api = db.DB_log_api


# Функции

def print_telegram(text_mess):
    print(text_mess)
    for _ in set_id:
        tele_bot.send_message(_, text_mess)


def api_ping(market_place_def):
    if market_place_def == 'Poloniex':
        ping_result = polo.returnBalances()['BTC']

    elif market_place_def == 'Binance':
        ping_result = float(client.get_asset_balance(asset='BTC')['free'])

    elif market_place_def == 'Kraken':
        ping_result = kraken.query_private('Balance')

    elif market_place_def == 'Bittrex':
        ping_result = my_bittrex.get_balance('BTC')['result']['Available']

    else:
        print_telegram('Unknown market API !')
        ping_result = -1

    return ping_result
