from pymongo import MongoClient
from poloniex import Poloniex
from binance.client import Client
from bittrex.bittrex import *
import krakenex
import time
import telebot
import constants
import datetime
import sys

# import pandas as pd

api_key_polo = constants.api_key_polo
api_secret_polo = constants.api_secret_polo
polo = Poloniex(api_key_polo, api_secret_polo)

api_key_binance = constants.api_key_binance
api_secret_binance = constants.api_secret_binance
client = Client(api_key_binance, api_secret_binance)

api_key_kraken = constants.api_key_kraken
api_secret_kraken = constants.api_secret_kraken
kraken = krakenex.API(key=api_key_kraken, secret=api_secret_kraken)

api_key_bittrex = constants.api_key_bittrex
api_secret_bittrex = constants.api_secret_bittrex
my_bittrex = Bittrex(api_key_bittrex, api_secret_bittrex, api_version=API_V1_1)

token = constants.token
tele_bot = telebot.TeleBot(token)
set_id = constants.set_id

client_mongo = MongoClient('127.0.0.1', 27017)

# створення бази та колекції - виконується одноразово
# db = client_mongo['DB_bigbott']
# db_bot = db.create_collection('DB_bot')
# db_action = db.create_collection('DB_action')
# db_orders = db.create_collection('DB_orders')
# db_log_restart = db.create_collection('DB_log_restart')

# підєднатися до бази і колекції
db = client_mongo.DB_bigbott
DB_action_collection = db.DB_action
DB_bot_collection = db.DB_bot
DB_orders_collection = db.DB_orders
DB_log_restart_collection = db.DB_log_restart
db_log_api = db.DB_log_api

# записати бд в pandas
# data = pd.DataFrame(list(col.find()))
# print(data.head())
#
# data.to_csv('test.csv', sep=';')
count_attempt_try = 5


def print_telegram(text_mess):
    print(text_mess)
    for _ in set_id:
        tele_bot.send_message(_, text_mess)


def prod(_, array):
    p = 1
    if _ == 0:
        return p * (1 - array[0])
    else:
        return prod(_ - 1, array) * (1 - array[_])


def suma(_, array):
    if _ == 0:
        return array[_]
    else:
        return suma(_ - 1, array) + array[_]


def except_part_for_api(bot_id, type_api_def, count_attempt_def):
    global count_attempt_try
    if db_log_api.find({'id_bot': bot_id}).count() == 0:
        new_id_log_api = 1
    else:
        last_id_in_db_log_api = db_log_api.find({'id_bot': bot_id}).count() - 1
        new_id_log_api = db_log_api.find({'id_bot': bot_id})[last_id_in_db_log_api]['id_log_api'] + 1

    if 2 <= count_attempt_def <= count_attempt_try:
        db_log_api.delete_one({'_id': db_log_api.find_one({'id_bot': bot_id, 'id_log_api': new_id_log_api - 1})['_id']})
    else:
        pass

    if count_attempt_def == count_attempt_try:
        description_value = 'Stop and Restart after Ping by try. Attempt = ' + str(count_attempt_def)
        db_log_api.insert_one({'id_log_api': new_id_log_api,
                               'id_bot': bot_id,
                               'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               'type_api': type_api_def,
                               'description': description_value,
                               'trigger': 1
                               })
        sys.exit()

    else:
        description_value = 'Ping by try. Attempt = ' + str(count_attempt_def)
        db_log_api.insert_one({'id_log_api': new_id_log_api,
                               'id_bot': bot_id,
                               'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               'type_api': type_api_def,
                               'description': description_value,
                               'trigger': 0
                               })


# def_API


def api_list_of_open_orders(bot_id, market_place_def, currency_pair_def):
    list_open_order_number_def = []
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:

        try:
            list_open_order_number_def = []
            if market_place_def == 'Poloniex':
                open_orders = polo.returnOpenOrders(currency_pair_def)
                for _ in range(len(open_orders)):
                    list_open_order_number_def.append(open_orders[_]['orderNumber'])

            elif market_place_def == 'Binance':
                open_orders = client.get_open_orders(symbol=currency_pair_def)
                for _ in range(len(open_orders)):
                    list_open_order_number_def.append(open_orders[_]['orderId'])

            elif market_place_def == 'Kraken':
                open_orders = kraken.query_private('OpenOrders')
                list_open_order_number_def = list(open_orders['result']['open'].keys())

            elif market_place_def == 'Bittrex':
                open_orders = my_bittrex.get_open_orders(market=currency_pair_def)['result']
                for _ in range(len(open_orders)):
                    list_open_order_number_def.append(open_orders[_]['OrderUuid'])

            else:
                print_telegram('Unknown market API !')
                list_open_order_number_def = []

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Return open Orders', count_attempt)
            time.sleep(1)

    return list_open_order_number_def


def api_balance_coin(bot_id, market_place_def, coin_def):
    api_balance_coin_calc = -1

    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:

        try:
            if market_place_def == 'Poloniex':
                api_balance_coin_calc = polo.returnBalances()[coin_def]
            elif market_place_def == 'Binance':
                api_balance_coin_calc = float(client.get_asset_balance(asset=coin_def)['free'])
            elif market_place_def == 'Kraken':
                balance_def = kraken.query_private('Balance')
                balance_def = balance_def['result']
                new_balance = dict()
                for currency in balance_def:
                    # remove first symbol ('Z' or 'X'), but not for GNO or DASH
                    new_coin_name = currency[1:] if len(currency) == 4 and currency != "DASH" else currency
                    new_balance[new_coin_name] = balance_def[currency]
                api_balance_coin_calc = float(new_balance[coin_def])
            elif market_place_def == 'Bittrex':
                api_balance_coin_calc = my_bittrex.get_balance(coin_def)['result']['Available']
            else:
                print_telegram('Unknown market API !')
                api_balance_coin_calc = -1

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Return Balance', count_attempt)
            time.sleep(1)

    return api_balance_coin_calc


def api_ticker_price_by_type(bot_id, market_place_def, coin_pair_def, type_of_price_def):
    api_ticker_price_calc = -1

    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            if market_place_def == 'Poloniex':
                if type_of_price_def == 'ask':
                    api_ticker_price_calc = polo.returnTicker()[coin_pair_def]['lowestAsk']
                elif type_of_price_def == 'bid':
                    api_ticker_price_calc = polo.returnTicker()[coin_pair_def]['highestBid']
                elif type_of_price_def == 'last':
                    api_ticker_price_calc = polo.returnTicker()[coin_pair_def]['last']
                else:
                    print_telegram('Unknown market API !')
                    api_ticker_price_calc = -1

            elif market_place_def == 'Binance':
                if type_of_price_def == 'ask':
                    api_ticker_price_calc = float(client.get_ticker(symbol=coin_pair_def)['askPrice'])
                elif type_of_price_def == 'bid':
                    api_ticker_price_calc = float(client.get_ticker(symbol=coin_pair_def)['bidPrice'])
                elif type_of_price_def == 'last':
                    api_ticker_price_calc = float(client.get_ticker(symbol=coin_pair_def)['lastPrice'])
                else:
                    print_telegram('Unknown market API !')
                    api_ticker_price_calc = -1

            elif market_place_def == 'Kraken':
                ticker_kraken = kraken.query_public('Ticker', {'pair': coin_pair_def})

                find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
                coin_def = find_one_in_db_bot_def['coin']
                coin_base_def = find_one_in_db_bot_def['coin_base']

                list_kraken_coins_without_xz = ['DASH', 'BCH', 'EOS', 'GNO']
                list_kraken_coins_base_with_x = ['XBT', 'ETH']

                if coin_def not in list_kraken_coins_without_xz:
                    if coin_base_def not in list_kraken_coins_base_with_x:
                        coin_pair_def = 'X' + str(coin_def) + 'Z' + str(coin_base_def)
                    else:
                        coin_pair_def = 'X' + str(coin_def) + 'X' + str(coin_base_def)
                elif coin_def == 'USDT':
                    coin_pair_def = 'USDTZUSD'
                else:
                    pass

                if type_of_price_def == 'ask':
                    api_ticker_price_calc = float(ticker_kraken['result'][coin_pair_def]['a'][0])
                elif type_of_price_def == 'bid':
                    api_ticker_price_calc = float(ticker_kraken['result'][coin_pair_def]['b'][0])
                elif type_of_price_def == 'last':
                    api_ticker_price_calc = float(ticker_kraken['result'][coin_pair_def]['c'][0])
                else:
                    print_telegram('Unknown market API !')
                    api_ticker_price_calc = -1

            elif market_place_def == 'Bittrex':
                if type_of_price_def == 'ask':
                    api_ticker_price_calc = my_bittrex.get_ticker(market=coin_pair_def)['result']['Ask']
                elif type_of_price_def == 'bid':
                    api_ticker_price_calc = my_bittrex.get_ticker(market=coin_pair_def)['result']['Bid']
                elif type_of_price_def == 'last':
                    api_ticker_price_calc = my_bittrex.get_ticker(market=coin_pair_def)['result']['Last']
                else:
                    print_telegram('Unknown market API !')
                    api_ticker_price_calc = -1

            else:
                print_telegram('Unknown market API !')

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Return Ticker Price', count_attempt)
            time.sleep(1)

    return api_ticker_price_calc


def api_order_cancel(bot_id, market_place_def, order_number_def):
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
            if market_place_def == 'Poloniex':
                polo.cancelOrder(order_number_def)
            elif market_place_def == 'Binance':
                currency_pair_def = find_one_in_db_bot_def['coin_pair_bot']
                client.cancel_order(symbol=currency_pair_def, orderId=order_number_def)
            elif market_place_def == 'Kraken':
                kraken.query_private('CancelOrder', {'txid': order_number_def})
            elif market_place_def == 'Bittrex':
                my_bittrex.cancel(order_number_def)
            else:
                print_telegram('Unknown market API !')

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Cancel', count_attempt)
            time.sleep(1)


def api_sell_limit(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_def, amount_sell_def):
    sell_order_number_calc = -1
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            amount_to_sell_calc = amount_to_sell_by_quota_calculation(market_place_def, coin_def, coin_base_def,
                                                                      rate_def, amount_sell_def)
            allow_amount = min_amount_in_order_calculation(market_place_def, coin_def)
            if allow_amount < amount_to_sell_calc:
                pass
            else:
                amount_to_sell_calc = allow_amount

            rate_formatted = price_in_order_formatting(market_place_def, currency_pair_def, rate_def)

            if market_place_def == 'Poloniex':
                api_sell_limit_calc = polo.sell(currency_pair_def, rate_formatted, amount_to_sell_calc)
                sell_order_number_calc = api_sell_limit_calc['orderNumber']
            elif market_place_def == 'Binance':
                api_sell_limit_calc = client.order_limit_sell(symbol=currency_pair_def, price=rate_formatted,
                                                              quantity=amount_to_sell_calc)
                sell_order_number_calc = api_sell_limit_calc['orderId']
            elif market_place_def == 'Kraken':
                api_sell_limit_calc = kraken.query_private('AddOrder',
                                                           {'pair': currency_pair_def,
                                                            'type': 'sell',
                                                            'price': rate_formatted,
                                                            'ordertype': 'limit',
                                                            'volume': amount_to_sell_calc})
                sell_order_number_calc = api_sell_limit_calc['result']['txid'][0]
            elif market_place_def == 'Bittrex':
                api_sell_limit_calc = my_bittrex.sell_limit(currency_pair_def, amount_to_sell_calc, rate_formatted)
                sell_order_number_calc = api_sell_limit_calc['result']['uuid']
            else:
                print('Unknown market API !')
                sell_order_number_calc = -2

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Open Sell Limit', count_attempt)
            time.sleep(1)

    if str(sell_order_number_calc) == '-2':
        print_telegram('Unknown market API (Problem with def api_sell_limit)! Stop bot № = {}'.format(bot_id))
        sys.exit()
    elif str(sell_order_number_calc) == '-1':
        print_telegram('Problem with def api_sell_limit (not in API). Stop bot № = {}'.format(bot_id))
        sys.exit()
    else:
        return sell_order_number_calc


def api_sell_market(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_plan_def,
                    amount_sell_def):
    sell_order_number_calc = -1
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            amount_to_sell_calc = amount_to_sell_by_quota_calculation(market_place_def, coin_def, coin_base_def,
                                                                      rate_plan_def, amount_sell_def)
            allow_amount = min_amount_in_order_calculation(market_place_def, coin_def)
            if allow_amount < amount_to_sell_calc:
                pass
            else:
                amount_to_sell_calc = allow_amount

            if market_place_def == 'Poloniex':
                rate_emulation_sell_calc = rate_marketprice_emulation_sell(market_place_def, rate_plan_def)
                api_sell_market_calc = polo.sell(currency_pair_def, rate_emulation_sell_calc, amount_to_sell_calc)
                sell_order_number_calc = api_sell_market_calc['orderNumber']
            elif market_place_def == 'Binance':
                api_sell_market_calc = client.order_market_sell(symbol=currency_pair_def, quantity=amount_to_sell_calc)
                sell_order_number_calc = api_sell_market_calc['orderId']
            elif market_place_def == 'Kraken':
                api_sell_market_calc = kraken.query_private('AddOrder',
                                                            {'pair': currency_pair_def,
                                                             'type': 'sell',
                                                             'ordertype': 'market',
                                                             'volume': amount_to_sell_calc})
                sell_order_number_calc = api_sell_market_calc['result']['txid'][0]
            elif market_place_def == 'Bittrex':
                rate_emulation_sell_calc = rate_marketprice_emulation_sell(market_place_def, rate_plan_def)
                api_sell_limit_calc = my_bittrex.sell_limit(currency_pair_def, amount_to_sell_calc,
                                                            rate_emulation_sell_calc)
                sell_order_number_calc = api_sell_limit_calc['result']['uuid']
            else:
                print('Unknown market API !')
                sell_order_number_calc = -2

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Open Sell Market', count_attempt)
            time.sleep(1)

    if str(sell_order_number_calc) == '-2':
        print_telegram('Unknown market API (Problem with def api_sell_limit)! Stop bot № = {}'.format(bot_id))
        sys.exit()
    elif str(sell_order_number_calc) == '-1':
        print_telegram('Problem with def api_sell_limit (not in API). Stop bot № = {}'.format(bot_id))
        sys.exit()
    else:
        return sell_order_number_calc


def api_buy_limit(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_def, amount_buy_def):
    buy_order_number_calc = -1
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            amount_to_buy_calc = amount_to_buy_by_quota_calculation(market_place_def, coin_def, coin_base_def,
                                                                    rate_def, amount_buy_def)
            allow_amount = min_amount_in_order_calculation(market_place_def, coin_def)
            if allow_amount < amount_to_buy_calc:
                pass
            else:
                amount_to_buy_calc = allow_amount

            rate_formatted = price_in_order_formatting(market_place_def, currency_pair_def, rate_def)

            if market_place_def == 'Poloniex':
                api_buy_limlit_calc = polo.buy(currency_pair_def, rate_formatted, amount_to_buy_calc)
                buy_order_number_calc = api_buy_limlit_calc['orderNumber']
            elif market_place_def == 'Binance':
                api_buy_limlit_calc = client.order_limit_buy(symbol=currency_pair_def, price=rate_formatted,
                                                             quantity=amount_to_buy_calc)
                buy_order_number_calc = api_buy_limlit_calc['orderId']
            elif market_place_def == 'Kraken':
                api_buy_limit_calc = kraken.query_private('AddOrder',
                                                          {'pair': currency_pair_def,
                                                           'type': 'buy',
                                                           'price': rate_formatted,
                                                           'ordertype': 'limit',
                                                           'volume': amount_to_buy_calc})
                buy_order_number_calc = api_buy_limit_calc['result']['txid'][0]
            elif market_place_def == 'Bittrex':
                api_buy_limlit_calc = my_bittrex.buy_limit(currency_pair_def, amount_to_buy_calc, rate_formatted)
                buy_order_number_calc = api_buy_limlit_calc['result']['uuid']
            else:
                print('Unknown market API !')
                buy_order_number_calc = -2

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Open Buy Limit', count_attempt)
            time.sleep(1)

    if str(buy_order_number_calc) == '-2':
        print_telegram('Unknown market API (Problem with def api_sell_limit)! Stop bot № = {}'.format(bot_id))
        sys.exit()
    elif str(buy_order_number_calc) == '-1':
        print_telegram('Problem with def api_sell_limit (not in API). Stop bot № = {}'.format(bot_id))
        sys.exit()
    else:
        return buy_order_number_calc


def api_buy_market(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_plan_def, amount_buy_def):
    buy_order_number_calc = -1
    global count_attempt_try
    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            amount_to_buy_calc = amount_to_buy_by_quota_calculation(market_place_def, coin_def, coin_base_def,
                                                                    rate_plan_def, amount_buy_def)
            allow_amount = min_amount_in_order_calculation(market_place_def, coin_def)
            if allow_amount < amount_to_buy_calc:
                pass
            else:
                amount_to_buy_calc = allow_amount

            if market_place_def == 'Poloniex':
                rate_emulation_buy_calc = rate_marketprice_emulation_buy(market_place_def, rate_plan_def)
                api_buy_market_calc = polo.buy(currency_pair_def, rate_emulation_buy_calc, amount_to_buy_calc)
                buy_order_number_calc = api_buy_market_calc['orderNumber']
            elif market_place_def == 'Binance':
                api_buy_market_calc = client.order_market_buy(symbol=currency_pair_def, quantity=amount_to_buy_calc)
                buy_order_number_calc = api_buy_market_calc['orderId']
            elif market_place_def == 'Kraken':
                api_buy_market_calc = kraken.query_private('AddOrder',
                                                           {'pair': currency_pair_def,
                                                            'type': 'buy',
                                                            'ordertype': 'market',
                                                            'volume': amount_to_buy_calc})
                buy_order_number_calc = api_buy_market_calc['result']['txid'][0]
            elif market_place_def == 'Bittrex':
                rate_emulation_buy_calc = rate_marketprice_emulation_buy(market_place_def, rate_plan_def)
                api_buy_limlit_calc = my_bittrex.buy_limit(currency_pair_def, amount_to_buy_calc,
                                                           rate_emulation_buy_calc)
                buy_order_number_calc = api_buy_limlit_calc['result']['uuid']
            else:
                print('Unknown market API !')
                buy_order_number_calc = -2

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Open Buy Market', count_attempt)
            time.sleep(1)

    if str(buy_order_number_calc) == '-2':
        print_telegram('Unknown market API (Problem with def api_sell_limit)! Stop bot № = {}'.format(bot_id))
        sys.exit()
    elif str(buy_order_number_calc) == '-1':
        print_telegram('Problem with def api_sell_limit (not in API). Stop bot № = {}'.format(bot_id))
        sys.exit()
    else:
        return buy_order_number_calc


# def api_sell_loss(market_place_def, currency_pair_def, coin_def, coin_base_def, rate_plan_def, amount_sell_def):
#     amount_to_sell_calc = amount_to_sell_by_quota_calculation(market_place_def, coin_def, coin_base_def,
#                                                               rate_plan_def, amount_sell_def)
#     allow_amount = min_amount_in_order_calculation(market_place_def, coin_def)
#     if allow_amount < amount_to_sell_calc:
#         pass
#     else:
#         amount_to_sell_calc = allow_amount
#
#     if market_place_def == 'Poloniex':
#         sell_loss_order_number_calc = -1
#
#     elif market_place_def == 'Binance':
#         api_sell_loss_calc = client.create_order(symbol=currency_pair_def, side='SELL', type='STOP_LOSS_LIMIT',
#                                                  price=rate_plan_def, quantity=amount_to_sell_calc)
#         sell_loss_order_number_calc = api_sell_loss_calc['orderId']
#     else:
#         print('Unknown market API !')
#         sell_loss_order_number_calc = -1
#
#     return sell_loss_order_number_calc

# Def_helps_API


def price_in_order_formatting(market_place_def, currency_pair_def, rate_def):
    rate_formatted_def = rate_def
    if market_place_def == 'Poloniex':
        pass
    elif market_place_def == 'Binance':
        if currency_pair_def in ['BTCUSDT', 'ETHUSDT', 'BCCUSDT', 'LTCUSDT']:
            rate_formatted_def = round(rate_def, 2)
        else:
            pass
    elif market_place_def == 'Kraken':
        if currency_pair_def in ['XBTUSD']:
            rate_formatted_def = round(rate_def, 1)
        elif currency_pair_def in ['ETHUSD']:
            rate_formatted_def = round(rate_def, 2)
        elif currency_pair_def in ['ETHXBT']:
            rate_formatted_def = round(rate_def, 5)
        else:
            pass
    elif market_place_def == 'Bittrex':
        pass
    else:
        pass

    return rate_formatted_def


def amount_to_sell_by_quota_calculation(market_place_def, coin_def, coin_base_def, rate_def, amount_sell_def):
    total_for_sell = rate_def * amount_sell_def
    min_total_amount = min_total_amount_in_order_calculation(market_place_def, coin_base_def)

    if total_for_sell < min_total_amount:
        amount_sell_calc = (min_total_amount * 1.05) / rate_def
    else:
        amount_sell_calc = amount_sell_def

    min_amount = min_amount_in_order_calculation(market_place_def, coin_def)
    amount_sell_calc = max(amount_sell_calc, min_amount * 1.05)

    if market_place_def in ['Poloniex', 'Bittrex']:
        pass
    elif market_place_def == 'Binance':
        amount_sell_calc = int(amount_sell_calc) + float(str((amount_sell_calc - int(amount_sell_calc)))[1:8])
    elif market_place_def == 'Kraken':
        amount_sell_calc = int(amount_sell_calc) + float(str((amount_sell_calc - int(amount_sell_calc)))[1:8])
    else:
        pass

    return amount_sell_calc


# взагалі потрібно додати перевірку на те чи можна здійснити покупку чи ні, раптом кошти "закінчилися"
def amount_to_buy_by_quota_calculation(market_place_def, coin_def, coin_base_def, rate_def, amount_buy_def):
    total_for_buy = rate_def * amount_buy_def
    min_total_amount = min_total_amount_in_order_calculation(market_place_def, coin_base_def)

    if total_for_buy < min_total_amount:
        amount_buy_calc = (min_total_amount * 1.05) / rate_def
    else:
        amount_buy_calc = amount_buy_def

    min_amount = min_amount_in_order_calculation(market_place_def, coin_def)
    amount_buy_calc = max(amount_buy_calc, min_amount * 1.05)

    if market_place_def in ['Poloniex', 'Bittrex']:
        pass
    elif market_place_def == 'Binance':
        amount_buy_calc = int(amount_buy_calc) + float(str((amount_buy_calc - int(amount_buy_calc)))[1:8])
    elif market_place_def == 'Kraken':
        amount_buy_calc = int(amount_buy_calc) + float(str((amount_buy_calc - int(amount_buy_calc)))[1:8])
    else:
        pass

    return amount_buy_calc


def min_total_amount_in_order_calculation(market_place_def, coin_base_def):
    if market_place_def == 'Poloniex':
        # Poloniex не працює з обмеженням на amount, лише total
        if coin_base_def == 'BTC':
            min_total_amount_calc = 0.0001
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.0001
        else:
            min_total_amount_calc = 1

    elif market_place_def == 'Binance':
        # Binance працює з обмеженням на total та на amount одночасно
        if coin_base_def == 'BTC':
            min_total_amount_calc = 0.001
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.01
        else:
            min_total_amount_calc = 10

    elif market_place_def == 'Kraken':
        # kraken не працює з обмеженням на total, лише amount
        min_total_amount_calc = 0

    elif market_place_def == 'Bittrex':
        # Bittrex ПЕРЕВІРИТИ чи працює з обмеженням на total та amount
        if coin_base_def == 'BTC':
            min_total_amount_calc = 0.001
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.001
        else:
            min_total_amount_calc = 1
    else:
        min_total_amount_calc = -1
        print_telegram('Unknown market API !')

    return min_total_amount_calc


def min_amount_in_order_calculation(market_place_def, coin_def):
    if market_place_def == 'Poloniex':
        # Poloniex не працює з обмеженням на amount, лише total
        min_amount_calc = 0

    elif market_place_def == 'Binance':
        # Binance працює з обмеженням на total та на amount одночасно
        if coin_def == 'BTC':
            min_amount_calc = 0.001
        elif coin_def == 'ETH':
            min_amount_calc = 0.01
        else:
            min_amount_calc = 0.001

    elif market_place_def == 'Kraken':
        # kraken не працює з обмеженням на total, лише amount
        if coin_def in ['XBT', 'BCH']:
            min_amount_calc = 0.002
        elif coin_def == 'ETH':
            min_amount_calc = 0.02
        elif coin_def in ['XMR', 'LTC', 'MLN']:
            min_amount_calc = 0.1
        else:
            min_amount_calc = 0.002

    elif market_place_def == 'Bittrex':
        # Bittrex ПЕРЕВІРИТИ чи працює з обмеженням на total та amount
        if coin_def == 'BTC':
            min_amount_calc = 0.001
        elif coin_def == 'ETH':
            min_amount_calc = 0.001
        else:
            min_amount_calc = 0.001
    else:
        min_amount_calc = -1
        print_telegram('Unknown market API !')

    return min_amount_calc


def rate_marketprice_emulation_sell(market_place_def, rate_def):
    if market_place_def in ['Poloniex', 'Bittrex']:
        rate_marketprice_emulation_sell_calc = rate_def * 0.8
    else:
        rate_marketprice_emulation_sell_calc = rate_def

    return rate_marketprice_emulation_sell_calc


def rate_marketprice_emulation_buy(market_place_def, rate_def):
    if market_place_def in ['Poloniex', 'Bittrex']:
        rate_marketprice_emulation_buy_calc = rate_def * 1.2
    else:
        rate_marketprice_emulation_buy_calc = rate_def

    return rate_marketprice_emulation_buy_calc


# df_DB


def insert_all_to_db_bot(bot_id, name_bot, market_place_bot, coin_pair_bot, model_type_bot, numbers_of_steps_bot,
                         s_amounts, procents_bot_def, procents_loss_bot_def, procents_up_r_def, procents_up_r_fin_def,
                         loss_max_count_bot_def, time_sleep_steps_bot_def, time_sleep_check_result_bot_def,
                         time_sleep_market_bot_def, profit_bot_def, t_step_action_def, id_action_open_def,
                         id_order_sell_open_def, id_order_buy_open_def, id_order_sell_loss_open_def, status_bot_def,
                         date_wait_bot_def, step_def, path_bot_def, id_user_def, coin_def, coin_base_def):
    DB_bot_collection.insert_one({
        'id_bot': bot_id,
        'name_bot': name_bot,
        'market_place_bot': market_place_bot,
        'coin_pair_bot': coin_pair_bot,
        'model_type_bot': model_type_bot,
        'numbers_of_steps_bot': numbers_of_steps_bot,
        'S_amounts': s_amounts,
        'procents_bot': procents_bot_def,
        'procents_loss_bot': procents_loss_bot_def,
        'procents_up_r': procents_up_r_def,
        'procents_up_r_fin': procents_up_r_fin_def,
        'loss_max_count_bot': loss_max_count_bot_def,
        'time_sleep_steps_bot': time_sleep_steps_bot_def,
        'time_sleep_check_result_bot': time_sleep_check_result_bot_def,
        'time_sleep_market_bot': time_sleep_market_bot_def,
        'profit_bot': profit_bot_def,
        't_step_action': t_step_action_def,
        'id_action_open': id_action_open_def,
        'id_order_sell_open': id_order_sell_open_def,
        'id_order_buy_open': id_order_buy_open_def,
        'id_order_sell_loss_open': id_order_sell_loss_open_def,
        'status_bot': status_bot_def,
        'date_wait_bot': date_wait_bot_def,
        'step': step_def,
        'path_bot': path_bot_def,
        'id_user': id_user_def,
        'coin': coin_def,
        'coin_base': coin_base_def,
        'PID_list': [-1, -1, -1]
    })


def insert_first_part_of_db_action(id_action_previous_def, bot_id, t_step_previous_def, t_steps_action, type_flag_def,
                                   order_parent_action_def, price_p0_action_def, price_action_def, c_amount_action_def,
                                   k_count_coin_action_def, b_amount_action_def, p_price_action_def, profit_action_def,
                                   profit_total_action_def):
    new_id_action = DB_action_collection.count() + 1
    date_record_action = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DB_action_collection.insert_one({
        'id_action': new_id_action,
        'id_action_previous': id_action_previous_def,
        'id_bot': bot_id,
        'date_action': date_record_action,
        't_step_previous': t_step_previous_def,
        't_steps_action': t_steps_action,
        'type_flag': type_flag_def,
        'order_parent_action': order_parent_action_def,
        'price_p0_action': price_p0_action_def,
        'price_action': price_action_def,
        'C_amount_action': c_amount_action_def,
        'K_count_coin_action': k_count_coin_action_def,
        'B_amount_action': b_amount_action_def,
        'P_price_action': p_price_action_def,
        'profit_action': profit_action_def,
        'profit_total_action': profit_total_action_def,
        'restart_type_action': [1, 1, 1],
        'date_wait_action': date_record_action,
        'status_action': 'Open'
    })

    s_amound_def = DB_bot_collection.find_one({'id_bot': bot_id})['S_amounts']

    if t_steps_action == -1:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [1, 0, 1],
                                                  'sell_order_number_action': 1}})
    elif 0 <= t_steps_action < len(s_amound_def) - 1:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [0, 0, 1]}})
    else:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [0, 1, 1]}})

    return new_id_action


def calculation_new_action(bot_id, order_number_def, t_def):
    find_one_in_db_orders_def = DB_orders_collection.find_one({'id_bot': bot_id, 'order_number': order_number_def})
    type_order_def = find_one_in_db_orders_def['type_order']
    type_flag_def = find_one_in_db_orders_def['type_flag']

    currency_pair_def = DB_bot_collection.find_one({'id_bot': bot_id})['coin_pair_bot']
    market_place_def = DB_bot_collection.find_one({'id_bot': bot_id})['market_place_bot']
    p0_def = api_ticker_price_by_type(bot_id, market_place_def, currency_pair_def, 'bid')

    find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
    id_action_previous_def = find_one_in_db_bot_def['id_action_open']
    find_one_previous_action_def = DB_action_collection.find_one({'id_bot': bot_id,
                                                                  'id_action': id_action_previous_def})

    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': id_action_previous_def},
                                    {'$set': {'status_action': 'Complete'}})
    t_def = t_def
    t_step_previous_def = find_one_in_db_bot_def['t_step_action']

    price_action_def = find_one_in_db_orders_def['result_rate_order']
    k_count_coin_action_previous_def = find_one_previous_action_def['K_count_coin_action']
    c_amount_action_previous_def = find_one_previous_action_def['C_amount_action']
    result_total_order_previous = find_one_in_db_orders_def['result_total_order']
    result_amount_coin_order_previous = find_one_in_db_orders_def['result_amount_coin_order']

    if type_order_def == 'Sell':
        type_flag_def = find_one_in_db_orders_def['type_flag']

        if type_flag_def == 'sell_part':
            price_p0_action_def = p0_def
            c_amount_action_def = price_action_def * k_count_coin_action_previous_def - result_total_order_previous
            k_count_coin_action_def = k_count_coin_action_previous_def - result_amount_coin_order_previous
            b_amount_action_def = price_action_def * k_count_coin_action_def
            p_price_action_def = c_amount_action_def / k_count_coin_action_def
            profit_action_def = result_total_order_previous - c_amount_action_previous_def + c_amount_action_def
            profit_total_action_def = find_one_in_db_bot_def['profit_bot'] + profit_action_def
        else:
            # type_flag_def == 'sell_all'
            price_p0_action_def = p0_def
            c_amount_action_def = price_action_def * k_count_coin_action_previous_def - result_total_order_previous
            k_count_coin_action_def = k_count_coin_action_previous_def - result_amount_coin_order_previous
            b_amount_action_def = price_action_def * k_count_coin_action_def
            p_price_action_def = p0_def
            profit_action_def = result_total_order_previous - c_amount_action_previous_def
            profit_total_action_def = find_one_in_db_bot_def['profit_bot'] + profit_action_def

    elif type_order_def == 'Buy':
        price_p0_action_def = find_one_previous_action_def['price_p0_action']
        c_amount_action_def = c_amount_action_previous_def + result_total_order_previous
        k_count_coin_action_def = k_count_coin_action_previous_def + result_amount_coin_order_previous
        b_amount_action_def = price_action_def * k_count_coin_action_def
        p_price_action_def = c_amount_action_def / k_count_coin_action_def
        profit_action_def = 0
        profit_total_action_def = find_one_in_db_bot_def['profit_bot'] + profit_action_def

    else:
        # type_order_def == 'Sell_loss':
        price_p0_action_def = find_one_previous_action_def['price_p0_action']
        c_amount_action_def = price_action_def * k_count_coin_action_previous_def - result_total_order_previous
        k_count_coin_action_def = k_count_coin_action_previous_def - result_amount_coin_order_previous
        b_amount_action_def = price_action_def * k_count_coin_action_def
        p_price_action_def = p0_def
        profit_action_def = result_total_order_previous - c_amount_action_previous_def
        profit_total_action_def = find_one_in_db_bot_def['profit_bot'] + profit_action_def

    id_action_previous_def = round(id_action_previous_def, 8)
    price_p0_action_def = round(price_p0_action_def, 8)
    price_action_def = round(price_action_def, 8)
    c_amount_action_def = round(c_amount_action_def, 8)
    k_count_coin_action_def = round(k_count_coin_action_def, 8)
    b_amount_action_def = round(b_amount_action_def, 8)
    p_price_action_def = round(p_price_action_def, 8)
    profit_action_def = round(profit_action_def, 8)
    profit_total_action_def = round(profit_total_action_def, 8)

    id_result_action_def = insert_first_part_of_db_action(id_action_previous_def, bot_id, t_step_previous_def, t_def,
                                                          type_flag_def, order_number_def, price_p0_action_def,
                                                          price_action_def, c_amount_action_def,
                                                          k_count_coin_action_def, b_amount_action_def,
                                                          p_price_action_def, profit_action_def,
                                                          profit_total_action_def)
    DB_bot_collection.update_one({'id_bot': bot_id},
                                 {'$set': {
                                     'id_action_open': id_result_action_def,
                                     'profit_bot': profit_total_action_def
                                 }})

    if type_order_def == 'Buy':
        number_def = find_one_previous_action_def['buy_counts_coin_plan_action']
        return id_result_action_def, number_def
    else:
        return id_result_action_def


def update_sell_part_in_db_action(bot_id, action_id, sell_price, sell_count_coin):
    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {
                                        'sell_price_action': sell_price,
                                        'sell_count_coin_action': sell_count_coin
                                    }})


def update_sell_number_to_all(bot_id, action_id, sell_order_number_def):
    list_of_restart = DB_action_collection.find_one({'id_bot': bot_id, 'id_action': action_id})['restart_type_action']
    list_of_restart[0] = sell_order_number_def

    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {'sell_order_number_action': sell_order_number_def,
                                              'restart_type_action': list_of_restart}})
    DB_bot_collection.update_one({'id_bot': bot_id},
                                 {'$set': {'id_order_sell_open': sell_order_number_def}})


def update_buy_part_in_db_action(bot_id, action_id, buy_price, buy_count_coin, buy_counts_coin_plan):
    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {
                                        'buy_price_action': buy_price,
                                        'buy_count_coin_action': buy_count_coin,
                                        'buy_counts_coin_plan_action': buy_counts_coin_plan
                                    }})


def update_buy_number_to_all(bot_id, action_id, buy_order_number_def):
    list_of_restart = DB_action_collection.find_one({'id_bot': bot_id, 'id_action': action_id})['restart_type_action']
    list_of_restart[1] = buy_order_number_def

    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {'buy_order_number_action': buy_order_number_def,
                                              'restart_type_action': list_of_restart}})
    DB_bot_collection.update_one({'id_bot': bot_id},
                                 {'$set': {'id_order_buy_open': buy_order_number_def}})


def update_sell_loss_in_db_action(bot_id, action_id, sell_loss_price, sell_loss_count_coin, sell_loss_order_number_def):
    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {
                                        'sell_loss_price_action': sell_loss_price,
                                        'sell_loss_count_coin_action': sell_loss_count_coin,
                                        'sell_loss_order_number_action': sell_loss_order_number_def
                                    }})


def update_sell_loss_number_to_all(bot_id, action_id, sell_loss_order_number_def):
    list_of_restart = DB_action_collection.find_one({'id_bot': bot_id, 'id_action': action_id})['restart_type_action']
    list_of_restart[-1] = sell_loss_order_number_def
    list_of_restart[0] = 1

    DB_action_collection.update_one({'id_bot': bot_id, 'id_action': action_id},
                                    {'$set': {'sell_loss_order_number_action': sell_loss_order_number_def,
                                              'restart_type_action': list_of_restart}})
    DB_bot_collection.update_one({'id_bot': bot_id},
                                 {'$set': {'id_order_sell_loss_open': sell_loss_order_number_def}})


def insert_first_part_of_db_orders(bot_id, order_number_def, type_order_def, type_global_order_def, type_flag_def,
                                   rate_plan_order_def, rate_order_def, amount_coin_order_def, total_amount_order_def):
    new_id_order = DB_orders_collection.count() + 1
    date_record_action = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
    coin_pair = find_one_in_db_bot_def['coin_pair_bot']
    id_action_def = find_one_in_db_bot_def['id_action_open']
    DB_orders_collection.insert_one({
        'id_order': new_id_order,
        'id_bot': bot_id,
        'id_action': id_action_def,
        'order_number': order_number_def,
        'date_order': date_record_action,
        'coin_pair_order': coin_pair,
        'type_order': type_order_def,
        'type_global_order': type_global_order_def,
        'type_flag': type_flag_def,
        'rate_plan_order': rate_plan_order_def,
        'rate_order': rate_order_def,
        'amount_coin_order': amount_coin_order_def,
        'total_amount_order': total_amount_order_def,
        'status_order': 'Open'})
    return new_id_order


def update_db_order_result(market_place_def, bot_id, order_number_def):
    global count_attempt_try

    count_attempt = 0
    while count_attempt < count_attempt_try:
        try:
            cursor = DB_orders_collection.find_one({'id_bot': bot_id, 'order_number': order_number_def})
            amount_coin_order_def = cursor['amount_coin_order']
            total_amount_order_def = cursor['total_amount_order']
            type_order_def = cursor['type_order']

            if market_place_def == 'Poloniex':
                result = polo.returnOrderTrades(order_number_def)
                all_amount = 0
                all_total = 0
                list_trades_id = []
                product_price_amount = 0
                for _ in range(0, len(result)):
                    all_amount = all_amount + result[_]['amount']
                    all_total = all_total + result[_]['total']
                    list_trades_id.append(result[_]['tradeID'])
                    product_price_amount = product_price_amount + result[_]['amount'] * result[_]['rate']

                result_rate_order = product_price_amount / all_amount
                date = result[0]['date']

                diff_amount = amount_coin_order_def - all_amount
                diff_total = total_amount_order_def - all_total

                if type_order_def.lower() == 'sell':
                    fee_all_def = 0
                    for _ in range(len(result)):
                        fee_all_def = fee_all_def + round(result[_]['amount'] * result[_]['rate'] * result[_]['fee'], 8)

                    result_amount_coin_order_minus_fee = all_amount
                    result_amount_coin_order_plus_fee = all_amount
                    result_total_order_minus_fee = all_total
                    result_total_order_plus_fee = all_total + fee_all_def

                    result_fee_in_coin_from_amount = 0
                    result_fee_in_coin_base_from_total = fee_all_def
                    result_fee = result_fee_in_coin_base_from_total + result_fee_in_coin_from_amount * result_rate_order

                else:
                    fee_all_def = 0
                    for _ in range(len(result)):
                        fee_all_def = fee_all_def + round(result[_]['amount'] * result[_]['fee'], 8)

                    result_amount_coin_order_minus_fee = all_amount - fee_all_def
                    result_amount_coin_order_plus_fee = all_amount
                    result_total_order_minus_fee = all_total
                    result_total_order_plus_fee = all_total

                    result_fee_in_coin_from_amount = fee_all_def
                    result_fee_in_coin_base_from_total = 0
                    result_fee = result_fee_in_coin_base_from_total + result_fee_in_coin_from_amount * result_rate_order

                DB_orders_collection.update_one({'id_bot': bot_id, 'order_number': order_number_def},
                                                {'$set': {
                                                    'result_amount_coin_order_minus_fee':
                                                        result_amount_coin_order_minus_fee,
                                                    'result_amount_coin_order_plus_fee':
                                                        result_amount_coin_order_plus_fee,
                                                    'result_total_order_minus_fee': result_total_order_minus_fee,
                                                    'result_total_order_plus_fee': result_total_order_plus_fee,
                                                    'result_fee_in_coin_base_from_total':
                                                        result_fee_in_coin_base_from_total,
                                                    'result_fee_in_coin_from_amount': result_fee_in_coin_from_amount,
                                                    'result_fee': result_fee
                                                }})

            elif market_place_def == 'Binance':
                coin_pair_def = DB_bot_collection.find_one({'id_bot': bot_id})['coin_pair_bot']
                trades_result = client.get_my_trades(symbol=coin_pair_def)
                list_result = []
                for _ in range(len(trades_result)):
                    if trades_result[_]['orderId'] == order_number_def:
                        list_result.append(trades_result[_])
                    else:
                        pass

                all_amount = 0
                all_total = 0
                fee_all_def = 0
                list_trades_id = []
                for _ in range(len(list_result)):
                    all_amount = all_amount + float(list_result[_]['qty'])
                    all_total = all_total + float(list_result[_]['price']) * float(list_result[_]['qty'])
                    fee_all_def = fee_all_def + float(list_result[_]['commission'])
                    list_trades_id.append(list_result[_]['id'])

                result_rate_order = all_total / all_amount

                if type_order_def.lower() == 'sell':
                    result_amount_coin_order_minus_fee = all_amount
                    result_amount_coin_order_plus_fee = all_amount
                    result_total_order_minus_fee = all_total
                    result_total_order_plus_fee = all_total + fee_all_def

                    result_fee_in_coin_from_amount = 0
                    result_fee_in_coin_base_from_total = fee_all_def
                    result_fee = result_fee_in_coin_base_from_total + result_fee_in_coin_from_amount * result_rate_order
                else:

                    result_amount_coin_order_minus_fee = all_amount - fee_all_def
                    result_amount_coin_order_plus_fee = all_amount
                    result_total_order_minus_fee = all_total
                    result_total_order_plus_fee = all_total

                    result_fee_in_coin_from_amount = fee_all_def
                    result_fee_in_coin_base_from_total = 0
                    result_fee = result_fee_in_coin_base_from_total + result_fee_in_coin_from_amount * result_rate_order

                DB_orders_collection.update_one({'id_bot': bot_id, 'order_number': order_number_def},
                                                {'$set': {
                                                    'result_amount_coin_order_minus_fee':
                                                        result_amount_coin_order_minus_fee,
                                                    'result_amount_coin_order_plus_fee':
                                                        result_amount_coin_order_plus_fee,
                                                    'result_total_order_minus_fee': result_total_order_minus_fee,
                                                    'result_total_order_plus_fee': result_total_order_plus_fee,
                                                    'result_fee_in_coin_base_from_total':
                                                        result_fee_in_coin_base_from_total,
                                                    'result_fee_in_coin_from_amount': result_fee_in_coin_from_amount,
                                                    'result_fee': result_fee
                                                }})

                date = datetime.datetime.fromtimestamp(int(list_result[0]['time'] / 1000)).strftime('%Y-%m-%d %H:%M:%S')

                check_order_status = client.get_order(orderId=order_number_def, symbol=coin_pair_def)['status'].lower()
                if check_order_status == 'filled':
                    diff_amount = 0
                    diff_total = 0
                else:
                    diff_amount = amount_coin_order_def - all_amount
                    diff_total = total_amount_order_def - all_total

            elif market_place_def == 'Kraken':
                trades_result = kraken.query_private('ClosedOrders')
                order_trade_result = trades_result['result']['closed'][order_number_def]
                date = datetime.datetime.fromtimestamp(int(order_trade_result['closetm'])).strftime('%Y-%m-%d %H:%M:%S')
                result_rate_order = float(order_trade_result['price'])
                all_amount = float(order_trade_result['vol_exec'])
                all_total = float(order_trade_result['cost'])
                list_trades_id = [order_number_def]

                diff_amount = amount_coin_order_def - all_amount
                diff_total = total_amount_order_def - all_total

            elif market_place_def == 'Bittrex':
                currency_pair_def = DB_bot_collection.find_one({'id_bot': bot_id})['coin_pair_bot']
                trades_result = my_bittrex.get_order_history(currency_pair_def)['result']
                list_result = []
                for _ in range(len(trades_result)):
                    if trades_result[_]['OrderUuid'] == order_number_def:
                        list_result.append(trades_result[_])
                    else:
                        pass

                all_amount = 0
                all_total = 0
                list_trades_id = []
                product_price_amount = 0
                _ = 0
                for _ in range(len(list_result)):
                    all_amount = all_amount + float(list_result[_]['Quantity'])
                    all_total = all_total + float(list_result[_]['Price'])
                    list_trades_id.append(list_result[_]['OrderUuid'])
                    product_price_amount = \
                        product_price_amount + list_result[_]['Quantity'] * list_result[_]['PricePerUnit']

                result_rate_order = product_price_amount / all_amount
                date = list_result[0]['Closed']

                diff_amount = amount_coin_order_def - all_amount
                diff_total = total_amount_order_def - all_total

            else:
                result_rate_order = 0
                all_amount = 0
                all_total = 0
                list_trades_id = []
                date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                diff_amount = 0
                diff_total = 0
                print('Unknown market_place!')

            DB_orders_collection.update_one({'id_bot': bot_id, 'order_number': order_number_def},
                                            {'$set': {
                                                'status_order': 'Compelete',
                                                'result_rate_order': result_rate_order,
                                                'result_amount_coin_order': all_amount,
                                                'result_total_order': all_total,
                                                'result_trades_id_order': list_trades_id,
                                                'result_date_order': date,
                                                'open_amount_coin_order': diff_amount,
                                                'open_total_order': diff_total
                                            }})

            count_attempt = count_attempt_try

        except:
            count_attempt = count_attempt + 1
            except_part_for_api(bot_id, 'API Order Trade History', count_attempt)
            time.sleep(1)


def update_db_order_cancel(bot_id, order_number_def):
    DB_orders_collection.update_one({'id_bot': bot_id, 'order_number': order_number_def},
                                    {'$set': {
                                        'status_order': 'Cancel',
                                        'result_rate_order': 0,
                                        'result_amount_coin_order': 0,
                                        'result_total_order': 0,
                                        'result_trades_id_order': 0,
                                        'result_date_order': 0,
                                        'open_amount_coin_order': 0,
                                        'open_total_order': 0
                                    }})


info_bot = db.DB_bot.find_one({'id_bot': 0})
print(info_bot)

id_bot = info_bot['id_bot']
market_place = info_bot['market_place_bot']
procent = info_bot['procents_bot']
S_amounts = info_bot['S_amounts']
r_fin = info_bot['procents_up_r_fin']
procent_loss = info_bot['procents_loss_bot']
r = info_bot['procents_up_r']
currency_pair = info_bot['coin_pair_bot']
coin = info_bot['coin']
coin_base = info_bot['coin_base']
t = info_bot['t_step_action']
loss_max_count_bot = info_bot['loss_max_count_bot']
time_sleep_check_result_bot = info_bot['time_sleep_check_result_bot']
time_sleep_steps_bot = info_bot['time_sleep_steps_bot']
time_sleep_market_bot = info_bot['time_sleep_market_bot']
step = info_bot['step']
sell_order_number = info_bot['id_order_sell_open']
buy_order_number = info_bot['id_order_buy_open']
sell_loss_order_number = info_bot['id_order_sell_loss_open']
id_action_open = info_bot['id_action_open']
amount_coin_rest = 0

if info_bot['status_bot'] == 'In work':
    pass
else:
    print_telegram('You cann\'t run this bot, because DB_bot has status_bot not equal \n\'In work\'.')
    sys.exit()

if id_action_open == 0:
    t = -1

else:
    find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
    list_of_type_restart = find_one_in_db_action['restart_type_action']

    sell_type_restart = str(list_of_type_restart[0])
    buy_type_restart = str(list_of_type_restart[1])
    sell_loss_type_restart = str(list_of_type_restart[-1])

    list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)

    # restart = [N, N, 1]
    if (sell_type_restart != '1') and (sell_type_restart != '0') and \
            (buy_type_restart != '1') and (buy_type_restart != '0'):

        # добпрацювати варіанти згодом
        if (sell_order_number not in list_open_order_number) and (buy_order_number not in list_open_order_number):
            p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'ask')

            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                            {'$set': {'status_action': 'Complete'}})
            K_count_coin_action_previous = find_one_in_db_action['K_count_coin_action']

            update_db_order_result(market_place, id_bot, sell_order_number)
            update_db_order_result(market_place, id_bot, buy_order_number)

            find_one_in_db_orders_sell = DB_orders_collection.find_one({'id_bot': id_bot,
                                                                        'order_number': sell_order_number})
            find_one_in_db_orders_buy = DB_orders_collection.find_one({'id_bot': id_bot,
                                                                       'order_number': buy_order_number})

            result_dates_order_sell = datetime.datetime.strptime(find_one_in_db_orders_sell['result_dates_order'],
                                                                 "%Y-%m-%d %H:%M:%S")
            result_dates_order_buy = datetime.datetime.strptime(find_one_in_db_orders_buy['result_dates_order'],
                                                                "%Y-%m-%d %H:%M:%S")

            if result_dates_order_sell < result_dates_order_buy:
                # ------------ запис в action після sell
                t = 0
                id_result_action = calculation_new_action(id_bot, sell_order_number, t)

                number = find_one_in_db_action['buy_counts_coin_plan_action']
                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                {'$set': {'buy_counts_coin_plan_action': number}})

                # ------------ запис в action після buy
                t = -1
                id_result_action = calculation_new_action(id_bot, buy_order_number, t)[0]

            else:
                # ------------ запис в action після buy
                t = find_one_in_db_action['t_step_action'] + 1
                calculation_new_action(id_bot, buy_order_number, t)

                # ------------ запис в action після sell
                t = -1
                id_result_action = calculation_new_action(id_bot, sell_order_number, t)

            result_amount_coin_order_sell = find_one_in_db_orders_sell['result_amount_coin_order']
            result_amount_coin_order_buy = find_one_in_db_orders_buy['result_amount_coin_order']

            amount_sell = K_count_coin_action_previous - result_amount_coin_order_sell + result_amount_coin_order_buy
            count_coin = min(api_balance_coin(id_bot, market_place, coin), amount_sell)
            p_sell = p0
            update_sell_part_in_db_action(id_bot, id_result_action, p0, count_coin)

            sell_order_number = api_sell_market(id_bot, market_place, currency_pair, coin, coin_base, p_sell,
                                                count_coin)

            update_sell_number_to_all(id_bot, id_result_action, sell_order_number)

            order_number = sell_order_number
            type_order = 'Sell'
            type_global_order = 'Limit'
            type_flag = 'sell_all'
            rate_plan_order = p0
            rate_order = p_sell
            amount_count_order = amount_sell
            total_amount_order = rate_order * amount_count_order
            insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                           rate_plan_order, rate_order, amount_count_order, total_amount_order)

            t_step_action = 0
            id_order_sell_loss_open = 1
            status_bot = 'In work'
            date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {
                                             't_step_action': t_step_action,
                                             'id_order_sell_loss_open': id_order_sell_loss_open,
                                             'status_bot': status_bot,
                                             'date_wait_bot': date_wait_bot
                                         }})

            index_restart = 0
            while index_restart < 1:
                time.sleep(time_sleep_steps_bot)
                date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_wait_action = date_wait_bot

                DB_bot_collection.update_one({'id_bot': id_bot}, {'$set': {'date_wait_bot': date_wait_bot}})

                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                {'$set': {'date_wait_action': date_wait_action}})

                list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
                if sell_order_number not in list_open_order_number:
                    t = -1
                    update_db_order_result(market_place, id_bot, sell_order_number)
                    id_result_action = calculation_new_action(id_bot, sell_order_number, t)
                    index_restart = 1
                else:
                    pass

        else:
            pass

    # restart = [1, 0, 1] and [1, N, 1]
    elif (sell_type_restart == '1') and (sell_loss_type_restart == '1'):
        # restart = [1, 0, 1]
        if buy_type_restart == '0':
            t = -1
            pass
        # restart = [1, N, 1]
        else:
            list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
            if buy_order_number not in list_open_order_number:
                id_result_action = DB_bot_collection.find_one({'id_bot': id_bot})['id_action_open']
                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                {'$set': {'status_action': 'Complete'}})

                t_step_action = t
                id_order_sell_open = 0
                id_order_buy_open = buy_order_number
                id_order_sell_loss_open = 0
                status_bot = 'In work'
                date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                DB_bot_collection.update_one({'id_bot': id_bot},
                                             {'$set': {
                                                 't_step_action': t_step_action,
                                                 'id_order_sell_open': id_order_sell_open,
                                                 'id_order_buy_open': buy_order_number,
                                                 'id_order_sell_loss_open': id_order_sell_loss_open,
                                                 'status_bot': status_bot,
                                                 'date_wait_bot': date_wait_bot
                                             }})

                t = 0
                p0 = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_result_action})['price_action']

                p_sell = p0 * (1 + r / 100)
                p_buy = p0 * (1 - procent[1])
                buy_result_action = calculation_new_action(id_bot, buy_order_number, t)
                id_result_action = buy_result_action[0]
                number = buy_result_action[-1]

                find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_result_action})
                K_count_coin_action = find_one_in_db_action['K_count_coin_action']

                amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
                limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                             min_total_amount_in_order_calculation(market_place, coin_base) /
                                             (p_sell * 1.05))
                if amount_sell > limit_amount_for_order:
                    type_flag = 'sell_part'
                else:
                    amount_sell = K_count_coin_action
                    type_flag = 'sell_all'

                update_sell_part_in_db_action(id_bot, id_result_action, p_sell, amount_sell)

                sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base, p_sell,
                                                   amount_sell)

                update_sell_number_to_all(id_bot, id_result_action, sell_order_number)

                # записати дані ордеру в таблицю order
                order_number = sell_order_number
                type_order = 'Sell'
                type_global_order = 'Limit'
                rate_plan_order = p_sell
                rate_order = p_sell
                amount_count_order = amount_sell
                total_amount_order = amount_count_order * rate_order
                insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                               rate_plan_order, rate_order, amount_count_order, total_amount_order)

                # buy_count_coin_action
                k0 = number[1]
                update_buy_part_in_db_action(id_bot, id_result_action, p_buy, k0, number)

                buy_order_number = api_buy_limit(id_bot, market_place, currency_pair, coin, coin_base, p_buy, k0)

                update_buy_number_to_all(id_bot, id_result_action, buy_order_number)

                # записати дані про loss
                update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 0)

                order_number = buy_order_number
                type_order = 'Buy'
                type_global_order = 'Limit'
                type_flag = 'buy_all'
                rate_plan_order = p_buy
                rate_order = p_buy
                amount_count_order = k0
                total_amount_order = rate_order * amount_count_order
                insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                               rate_plan_order, rate_order, amount_count_order, total_amount_order)

                # дані для оновлення частини бази bot
                t_step_action = t
                id_order_sell_loss_open = 0
                status_bot = 'In work'
                date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                DB_bot_collection.update_one({'id_bot': id_bot},
                                             {'$set': {
                                                 't_step_action': t_step_action,
                                                 'id_order_sell_loss_open': id_order_sell_loss_open,
                                                 'status_bot': status_bot,
                                                 'date_wait_bot': date_wait_bot
                                             }})

                # записати дані ордеру в таблицю order

            else:
                find_one_in_db_orders = DB_orders_collection.find_one({'id_bot': id_bot,
                                                                       'order_number': buy_order_number})
                if find_one_in_db_orders['status_order'] == 'Open':
                    api_order_cancel(id_bot, market_place, buy_order_number)
                    update_db_order_cancel(id_bot, buy_order_number)
                else:
                    pass

                t = -1

    # restart = [0, 0, 1]
    elif (sell_type_restart == '0') and (buy_type_restart == '0') and (sell_loss_type_restart == '1'):
        find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
        id_action_previous = find_one_in_db_action['id_action_previous']
        DB_action_collection.delete_one({'_id': find_one_in_db_action['_id']})
        DB_bot_collection.update_one({'id_bot': id_bot}, {'$set': {'id_action_open': id_action_previous}})

    # restart = [N, 0, 1]
    elif (sell_type_restart != '0') and (sell_type_restart != '1') and \
            (buy_type_restart == '0') and (sell_loss_type_restart == '1'):

        if DB_bot_collection.find_one({'id_bot': id_bot})['stop_bot'] == 0:
            find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
            p0 = find_one_in_db_action['price_p0_action']
            K_count_coin_action = find_one_in_db_action['K_count_coin_action']
            p0_for_number = p0
            # buy_counts_coin_plan_action
            number = []
            for j in range(0, len(S_amounts)):
                if j == 0:
                    number.append(S_amounts[j] / p0_for_number)
                else:
                    number.append(S_amounts[j] / (p0_for_number * prod(j, procent)))

            # buy_price_action
            p_buy = p0 * (1 - procent[1])
            # buy_count_coin_action
            k0 = number[1]
            update_buy_part_in_db_action(id_bot, id_action_open, p_buy, k0, number)

            buy_order_number = api_buy_limit(id_bot, market_place, currency_pair, coin, coin_base, p_buy, k0)
            update_buy_number_to_all(id_bot, id_action_open, buy_order_number)

            order_number = buy_order_number
            type_order = 'Buy'
            type_global_order = 'Limit'
            type_flag = 'buy_all'
            rate_plan_order = p_buy
            rate_order = p_buy
            amount_count_order = k0
            total_amount_order = rate_order * amount_count_order
            insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                           rate_plan_order, rate_order, amount_count_order, total_amount_order)

            update_sell_loss_in_db_action(id_bot, id_action_open, 0, 0, 0)

            t = 0
            t_step_action = t
            id_order_sell_loss_open = 0
            status_bot = 'In work'
            date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {
                                             't_step_action': t_step_action,
                                             'id_order_sell_loss_open': id_order_sell_loss_open,
                                             'status_bot': status_bot,
                                             'date_wait_bot': date_wait_bot
                                         }})
        else:
            order_status = 0
            while order_status < 1:
                time.sleep(time_sleep_check_result_bot)
                date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_wait_action = date_wait_bot

                DB_bot_collection.update_one({'id_bot': id_bot},
                                             {'$set': {'date_wait_bot': date_wait_bot}})

                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                                {'$set': {'date_wait_action': date_wait_action}})

                list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)

                if sell_order_number not in list_open_order_number:
                    update_db_order_result(market_place, id_bot, sell_order_number)
                    id_result_action = calculation_new_action(id_bot, sell_order_number, t)

                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     'status_bot': 'Stop by DB stop_bot = 1',
                                                     'id_action_open': 0
                                                 }})
                    DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                                    {'$set': {'status_action': 'Complete'}})
                    print_telegram('Bot {} stopped!'.format(id_bot))
                    order_status = 1
                    sys.exit()

                else:
                    pass

    # restart = [0, N, 1]
    elif (sell_type_restart == '0') and (sell_loss_type_restart == '1') and \
            (buy_type_restart != '0') and (buy_type_restart != '1'):

        find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
        K_count_coin_action = find_one_in_db_action['K_count_coin_action']
        P_price_action = find_one_in_db_action['P_price_action']
        t = find_one_in_db_action['t_steps_action']

        # параметри для нового ордеру sell
        p_sell = P_price_action * (1 + r_fin / 100)
        amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
        limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                     min_total_amount_in_order_calculation(market_place, coin_base) / (p_sell * 1.05))
        if amount_sell > limit_amount_for_order:
            type_flag = 'sell_part'
        else:
            amount_sell = K_count_coin_action
            type_flag = 'sell_all'

        update_sell_part_in_db_action(id_bot, id_action_open, p_sell, amount_sell)

        sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base, p_sell, amount_sell)

        update_sell_number_to_all(id_bot, id_action_open, sell_order_number)

        order_number = sell_order_number
        type_order = 'Sell'
        type_global_order = 'Limit'
        rate_plan_order = p_sell
        rate_order = p_sell
        amount_count_order = amount_sell
        total_amount_order = rate_order * amount_count_order
        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                       rate_plan_order, rate_order, amount_count_order, total_amount_order)

        update_sell_loss_in_db_action(id_bot, id_action_open, 0, 0, 0)

        t_step_action = t
        id_order_sell_loss_open = 0
        status_bot = 'In work'
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        DB_bot_collection.update_one({'id_bot': id_bot},
                                     {'$set': {
                                         't_step_action': t_step_action,
                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                         'status_bot': status_bot,
                                         'date_wait_bot': date_wait_bot
                                     }})

    # restart = [0, 1, 1]
    elif (sell_type_restart == '0') and (buy_type_restart == '1') and (sell_loss_type_restart == '1'):
        p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')

        find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
        K_count_coin_action = find_one_in_db_action['K_count_coin_action']
        P_price_action = find_one_in_db_action['P_price_action']

        p_sell = P_price_action * (1 + r_fin / 100)
        amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
        limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                     min_total_amount_in_order_calculation(market_place, coin_base) / (p_sell * 1.05))
        if amount_sell > limit_amount_for_order:
            type_flag = 'sell_part'
        else:
            amount_sell = K_count_coin_action
            type_flag = 'sell_all'

        update_sell_part_in_db_action(id_bot, id_action_open, p_sell, amount_sell)
        sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base, p_sell, amount_sell)
        update_sell_number_to_all(id_bot, id_action_open, sell_order_number)

        update_buy_part_in_db_action(id_bot, id_action_open, 0, 0, 0)

        order_number = sell_order_number
        type_order = 'Sell'
        type_global_order = 'Limit'
        rate_plan_order = p_sell
        rate_order = p_sell
        amount_count_order = amount_sell
        total_amount_order = amount_count_order * rate_order
        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag, rate_plan_order,
                                       rate_order, amount_count_order, total_amount_order)
        p_loss = p0 * (1 - procent_loss / 100)

        update_sell_loss_in_db_action(id_bot, id_action_open, p_loss, K_count_coin_action, 1)

        #  виставлення stoploss
        t_step_action = len(S_amounts)
        id_order_buy_open = 1
        id_order_sell_loss_open = 1
        status_bot = 'In work'
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        DB_bot_collection.update_one({'id_bot': id_bot},
                                     {'$set': {
                                         't_step_action': t_step_action,
                                         'id_order_buy_open': buy_order_number,
                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                         'status_bot': status_bot,
                                         'date_wait_bot': date_wait_bot
                                     }})

    # restart = [N, 1, 1]
    elif (sell_type_restart != '1') and (sell_type_restart != '0') and \
            (buy_type_restart == '1') and (sell_loss_type_restart == '1'):
        t = DB_bot_collection.find_one({'id_bot': id_bot})['t_step_action']

    # restart = [1, 1, 0]
    elif (sell_type_restart == '1') and (buy_type_restart == '1') and (sell_loss_type_restart == '0'):
        # момент stoploss
        t = len(S_amounts)
        p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')
        p_sell_loss = p0

        find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_action_open})
        K_count_coin_stoploss = find_one_in_db_action['K_count_coin_action']

        # обміркувати цей момент, бо лише сповіщення в телеграм мало для подальших дій
        existing_count_coin_on_balance = api_balance_coin(id_bot, market_place, coin)
        if existing_count_coin_on_balance < K_count_coin_stoploss:
            K_count_coin_stoploss = existing_count_coin_on_balance
            print_telegram('WARRNING existing_count_coin_on_balance < K_count_coin_stoploss!!!')
        else:
            pass

        sell_loss_order_number = api_sell_market(id_bot, market_place, currency_pair, coin, coin_base, p_sell_loss,
                                                 K_count_coin_stoploss)

        update_sell_loss_number_to_all(id_bot, id_action_open, sell_loss_order_number)

        order_number = sell_loss_order_number
        type_order = 'Sell_loss'
        type_global_order = 'Limit'
        type_flag = 'sell_all'
        rate_plan_order = p0
        rate_order = p_sell_loss
        amount_count_order = K_count_coin_stoploss
        total_amount_order = rate_order * amount_count_order
        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag, rate_plan_order,
                                       rate_order, amount_count_order, total_amount_order)
        t_step_action = t
        id_order_sell_open = 1
        id_order_buy_open = 1
        status_bot = 'In work'
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        DB_bot_collection.update_one({'id_bot': id_bot},
                                     {'$set': {
                                         't_step_action': t,
                                         'id_order_sell_open': id_order_sell_open,
                                         'id_order_buy_open': id_order_buy_open,
                                         'status_bot': status_bot,
                                         'date_wait_bot': date_wait_bot
                                     }})

        index_stoploss = 0
        while index_stoploss < 1:
            time.sleep(time_sleep_steps_bot)

            date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_wait_action = date_wait_bot

            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {'date_wait_bot': date_wait_bot}})

            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                            {'$set': {'date_wait_action': date_wait_action}})

            list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
            find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
            sell_loss_order_number = find_one_in_db_bot['id_order_sell_loss_open']

            if sell_loss_order_number not in list_open_order_number:
                t = -1
                update_db_order_result(market_place, id_bot, sell_loss_order_number)
                id_result_action = calculation_new_action(id_bot, sell_loss_order_number, t)

                index_stoploss = 1
                step = DB_bot_collection.find_one({'id_bot': id_bot})['step']
                step = step + 1
                # оновити значення полів для sell і sell_order_number
                update_sell_part_in_db_action(id_bot, id_result_action, 0, 0)
                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                {'$set': {'sell_order_number_action': 1}})
                # оновлений запис в базі action про стан loss
                update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 1)

                # в базі bot оновлюємо запис про актуальний стан action
                DB_bot_collection.update_one({'id_bot': id_bot},
                                             {'$set': {
                                                 'id_order_sell_open': 1,
                                                 'id_order_sell_loss_open': 1,
                                                 'step': step
                                             }})

            else:
                pass

        if DB_bot_collection.find_one({'id_bot': id_bot})['stop_bot'] == 1:
            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {
                                             'status_bot': 'Stop by DB stop_bot = 1',
                                             'id_action_open': 0
                                         }})
            print_telegram('Bot {} stopped!'.format(id_bot))
            sys.exit()
        else:
            pass

    # restart = [1, 1, N]
    elif (sell_loss_type_restart != '1') and (sell_loss_type_restart != '0'):
        find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
        sell_loss_order_number = find_one_in_db_bot['id_order_sell_loss_open']

        if sell_loss_order_number not in list_open_order_number:
            t = -1
            update_db_order_result(market_place, id_bot, sell_loss_order_number)
            id_result_action = calculation_new_action(id_bot, sell_loss_order_number, t)
            update_sell_part_in_db_action(id_bot, id_result_action, 0, 0)
            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                            {'$set': {'sell_order_number_action': 1}})

            update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 1)
            step = DB_bot_collection.find_one({'id_bot': id_bot})['step']
            step = step + 1
            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {
                                             'id_order_sell_open': 1,
                                             'id_order_sell_loss_open': 1,
                                             'step': step
                                         }})
        else:
            index_stoploss = 0
            while index_stoploss < 1:
                time.sleep(time_sleep_steps_bot)

                date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                date_wait_action = date_wait_bot

                DB_bot_collection.update_one({'id_bot': id_bot},
                                             {'$set': {'date_wait_bot': date_wait_bot}})

                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': info_bot['id_action_open']},
                                                {'$set': {'date_wait_action': date_wait_action}})

                p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')

                list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
                find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
                sell_loss_order_number = find_one_in_db_bot['id_order_sell_loss_open']

                if sell_loss_order_number not in list_open_order_number:

                    t = -1
                    update_db_order_result(market_place, id_bot, sell_loss_order_number)
                    id_result_action = calculation_new_action(id_bot, sell_loss_order_number, t)

                    index_stoploss = 1
                    step = DB_bot_collection.find_one({'id_bot': id_bot})['step']
                    step = step + 1
                    # оновити значення полів для sell і sell_order_number
                    update_sell_part_in_db_action(id_bot, id_result_action, 0, 0)
                    DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                    {'$set': {'sell_order_number_action': 1}})
                    update_buy_part_in_db_action(id_bot, id_result_action, 0, 0, 0)
                    # оновлений запис в базі action про стан loss
                    update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 1)

                    # в базі bot оновлюємо запис про актуальний стан action
                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     'id_order_sell_open': 1,
                                                     'id_order_sell_loss_open': 1,
                                                     'step': step
                                                 }})

                else:
                    pass

        find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
        if find_one_in_db_bot['stop_bot'] == 1:
            DB_bot_collection.update_one({'id_bot': id_bot},
                                         {'$set': {
                                             'status_bot': 'Stop by DB stop_bot = 1',
                                             'id_action_open': 0
                                         }})
            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': find_one_in_db_bot['id_action_open']},
                                            {'$set': {'status_action': 'Complete'}})

            print_telegram('Bot {} stopped!'.format(id_bot))
            sys.exit()
        else:
            pass

    else:
        sys.exit('Uncorrect t, sell_order_number or buy_order_number')

# ЗАПУСК

while step <= loss_max_count_bot:

    if t == -1:
        # вход с restart = [1, 0, 1] или воообще без restart, при отсутствии первого action
        p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'ask')
        find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})

        if id_action_open == 0:
            id_action_previous = 0
            order_parent_action = 0
            t_step_previous = -1
            type_flag = 'buy_all'
        else:
            id_action_previous = find_one_in_db_bot['id_action_open']

            find_one_in_db_action = DB_action_collection.find_one({'id_action': id_action_previous})
            order_parent_action = find_one_in_db_action['order_parent_action']
            t_step_previous = find_one_in_db_action['t_steps_action']
            type_flag = find_one_in_db_action['type_flag']

        profit_total_action = find_one_in_db_bot['profit_bot']
        profit_action = 0
        price_p0_action = p0
        price_action = p0
        C_amount_action = 0
        K_count_coin_action = 0
        B_amount_action = 0
        P_price_action = p0

        id_result_action = insert_first_part_of_db_action(id_action_previous, id_bot, t_step_previous, t, type_flag,
                                                          order_parent_action, price_p0_action, price_action,
                                                          C_amount_action, K_count_coin_action, B_amount_action,
                                                          P_price_action, profit_action, profit_total_action)
        # записали restart = [1, 0, 1]

        # оновити значення полів для sell і sell_order_number
        update_sell_part_in_db_action(id_bot, id_result_action, 0, 0)

        # оновлений запис в базі action про стан loss
        update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 1)

        # в базі bot оновлюємо запис значення id_action
        DB_bot_collection.update_one({'id_bot': id_bot}, {'$set': {'id_action_open': id_result_action}})

        p0_for_number = p0
        # buy_counts_coin_plan_action
        number = []
        for j in range(0, len(S_amounts)):
            if j == 0:
                number.append(S_amounts[j] / p0_for_number)
            else:
                number.append(S_amounts[j] / (p0_for_number * prod(j, procent)))

        # buy_count_coin_action
        k0 = number[0]
        # count_coin_buy = max(0, k0 - amount_coin_rest)
        # sell_price_action
        p_sell = p0 * (1 + r / 100)
        # buy_price_action
        p_buy = p0 * (1 - procent[1])

        update_buy_part_in_db_action(id_bot, id_result_action, p0, k0, number)

        buy_order_number = api_buy_market(id_bot, market_place, currency_pair, coin, coin_base, p0, k0)

        update_buy_number_to_all(id_bot, id_result_action, buy_order_number)
        # записали restart = [1, N, 1]

        # запис в базу order
        order_number = buy_order_number
        type_order = 'Buy'
        type_global_order = 'Market'
        type_flag = 'buy_all'
        rate_plan_order = p0
        rate_order = rate_marketprice_emulation_buy(market_place, p0)
        amount_count_order = k0
        total_amount_order = rate_order * amount_count_order
        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag, rate_plan_order,
                                       rate_order, amount_count_order, total_amount_order)

        order_status = 0
        while order_status < 1:
            time.sleep(time_sleep_check_result_bot)
            date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            date_wait_action = date_wait_bot

            DB_bot_collection.update_one({'id_bot': id_bot}, {'$set': {'date_wait_bot': date_wait_bot}})

            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                            {'$set': {'date_wait_action': date_wait_action}})

            list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)

            if buy_order_number not in list_open_order_number:
                #  записати дані в базу orders про викокання ордеру
                update_db_order_result(market_place, id_bot, buy_order_number)
                order_status = 1
            else:
                pass

        #  оновити статус ордеру в таблиці action
        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                        {'$set': {'status_action': 'Complete'}})

        t_step_action = t
        id_order_sell_open = 0
        id_order_buy_open = buy_order_number
        id_order_sell_loss_open = 0
        status_bot = 'In work'
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        DB_bot_collection.update_one({'id_bot': id_bot},
                                     {'$set': {
                                         't_step_action': t_step_action,
                                         'id_order_sell_open': id_order_sell_open,
                                         'id_order_buy_open': buy_order_number,
                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                         'status_bot': status_bot,
                                         'date_wait_bot': date_wait_bot
                                     }})

        # ----------------------------------------------------------------------------
        # це вже новий запис в таблиці action, уважно записати дані у відповідні поля
        t = 0

        buy_result_action = calculation_new_action(id_bot, buy_order_number, t)
        # записали restart = [0, 0, 1]
        id_result_action = buy_result_action[0]
        number = buy_result_action[-1]

        find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_result_action})
        K_count_coin_action = find_one_in_db_action['K_count_coin_action']

        amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
        limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                     min_total_amount_in_order_calculation(market_place, coin_base) / (p_sell * 1.05))
        if amount_sell > limit_amount_for_order:
            type_flag = 'sell_part'
        else:
            amount_sell = K_count_coin_action
            type_flag = 'sell_all'

        update_sell_part_in_db_action(id_bot, id_result_action, p_sell, amount_sell)

        sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base, p_sell, amount_sell)

        update_sell_number_to_all(id_bot, id_result_action, sell_order_number)
        # записали restart = [N, 0, 1]

        # записати дані ордеру в таблицю order
        order_number = sell_order_number
        type_order = 'Sell'
        type_global_order = 'Limit'
        rate_plan_order = p_sell
        rate_order = p_sell
        amount_count_order = amount_sell
        total_amount_order = amount_count_order * rate_order

        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag, rate_plan_order,
                                       rate_order, amount_count_order, total_amount_order)

        # buy_count_coin_action
        k0 = number[1]
        update_buy_part_in_db_action(id_bot, id_result_action, p_buy, k0, number)

        buy_order_number = api_buy_limit(id_bot, market_place, currency_pair, coin, coin_base, p_buy, k0)

        update_buy_number_to_all(id_bot, id_result_action, buy_order_number)
        # записали restart = [N, N, 1]

        # записати дані про loss
        update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 0)

        order_number = buy_order_number
        type_order = 'Buy'
        type_global_order = 'Limit'
        type_flag = 'buy_all'
        rate_plan_order = p_buy
        rate_order = p_buy
        amount_count_order = k0
        total_amount_order = rate_order * amount_count_order
        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag, rate_plan_order,
                                       rate_order, amount_count_order, total_amount_order)

        # дані для оновлення частини бази bot
        t_step_action = t
        id_order_sell_loss_open = 0
        status_bot = 'In work'
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DB_bot_collection.update_one({'id_bot': id_bot},
                                     {'$set': {
                                         't_step_action': t_step_action,
                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                         'status_bot': status_bot,
                                         'date_wait_bot': date_wait_bot
                                     }})

    else:
        # випадок перезапуску - придумати згодом!!!
        pass

    while t >= 0:
        time.sleep(time_sleep_steps_bot)
        # оновлення полів date_wait
        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_wait_action = date_wait_bot

        find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
        id_result_action = find_one_in_db_bot['id_action_open']

        DB_bot_collection.update_one({'id_bot': id_bot}, {'$set': {'date_wait_bot': date_wait_bot}})

        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                        {'$set': {'date_wait_action': date_wait_action}})

        list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
        sell_order_number = find_one_in_db_bot['id_order_sell_open']
        buy_order_number = find_one_in_db_bot['id_order_buy_open']
        sell_loss_order_number = find_one_in_db_bot['id_order_sell_loss_open']

        find_one_sell_order = DB_orders_collection.find_one({'id_bot': id_bot, 'order_number': sell_order_number})
        status_order = find_one_sell_order['status_order']
        type_flag = find_one_sell_order['type_flag']

        # ------------------------------------------------------------------------------------------------------------
        if (sell_order_number not in list_open_order_number) and (status_order != 'Cancel'):
            # входим с restart = [N, N, 1] или [N, 1, 1]
            update_db_order_result(market_place, id_bot, sell_order_number)

            # скасувати попередній ордер для buy і написати, що результат скасовано в базі order
            find_one_in_db_orders = DB_orders_collection.find_one({'id_bot': id_bot, 'order_number': buy_order_number})
            if find_one_in_db_orders['status_order'] == 'Open':
                api_order_cancel(id_bot, market_place, buy_order_number)
                update_db_order_cancel(id_bot, buy_order_number)
            else:
                pass

            t = 0
            p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')

            id_result_action = calculation_new_action(id_bot, sell_order_number, t)

            if type_flag == 'sell_part':
                find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot, 'id_action': id_result_action})
                K_count_coin_action = find_one_in_db_action['K_count_coin_action']

                p0_for_number = p0

                if find_one_in_db_bot['stop_bot'] == 0:
                    # buy_counts_coin_plan_action
                    number = []
                    for j in range(0, len(S_amounts)):
                        if j == 0:
                            number.append(S_amounts[j] / p0_for_number)
                        else:
                            number.append(S_amounts[j] / (p0_for_number * prod(j, procent)))

                    time.sleep(time_sleep_market_bot)
                    # sell_price_action
                    p_sell = p0 * (1 + r / 100)

                    amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
                    limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                                 min_total_amount_in_order_calculation(market_place, coin_base) /
                                                 (p_sell * 1.05))
                    if amount_sell > limit_amount_for_order:
                        type_flag = 'sell_part'
                    else:
                        amount_sell = K_count_coin_action
                        type_flag = 'sell_all'

                    update_sell_part_in_db_action(id_bot, id_result_action, p_sell, amount_sell)

                    sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base, p_sell,
                                                       amount_sell)

                    update_sell_number_to_all(id_bot, id_result_action, sell_order_number)

                    # записати дані про sell в таблицю order
                    order_number = sell_order_number
                    type_order = 'Sell'
                    type_global_order = 'Limit'
                    rate_plan_order = p_sell
                    rate_order = p_sell
                    amount_count_order = amount_sell
                    total_amount_order = rate_order * amount_count_order
                    insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                   rate_plan_order, rate_order, amount_count_order, total_amount_order)

                    # buy_price_action
                    p_buy = p0 * (1 - procent[1])
                    # buy_count_coin_action
                    k0 = number[1]
                    update_buy_part_in_db_action(id_bot, id_result_action, p_buy, k0, number)

                    buy_order_number = api_buy_limit(id_bot, market_place, currency_pair, coin, coin_base, p_buy, k0)

                    update_buy_number_to_all(id_bot, id_result_action, buy_order_number)

                    # записати дані про buy в таблицю order
                    order_number = buy_order_number
                    type_order = 'Buy'
                    type_global_order = 'Limit'
                    type_flag = 'buy_all'
                    rate_plan_order = p_buy
                    rate_order = p_buy
                    amount_count_order = k0
                    total_amount_order = rate_order * amount_count_order
                    insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                   rate_plan_order, rate_order, amount_count_order, total_amount_order)

                    update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 0)

                    t_step_action = t
                    id_order_sell_loss_open = 0
                    status_bot = 'In work'
                    date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     't_step_action': t_step_action,
                                                     'id_order_sell_loss_open': id_order_sell_loss_open,
                                                     'status_bot': status_bot,
                                                     'date_wait_bot': date_wait_bot
                                                 }})
                else:
                    #        stop_bot == 1
                    limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                                 min_total_amount_in_order_calculation(market_place, coin_base) /
                                                 (p0 * 1.05))
                    if K_count_coin_action > limit_amount_for_order:
                        pass
                    else:
                        print_telegram('Ви не можете продати вказану кількість монет')
                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {'status_bot': 'Stop by DB stop_bot = 1'}})
                        print_telegram('Bot {} stopped!'.format(id_bot))
                        sys.exit()

                    update_sell_part_in_db_action(id_bot, id_result_action, p0, K_count_coin_action)

                    sell_order_number = api_sell_market(id_bot, market_place, currency_pair, coin, coin_base, p0,
                                                        K_count_coin_action)

                    update_sell_number_to_all(id_bot, id_result_action, sell_order_number)
                    update_buy_part_in_db_action(id_bot, id_result_action, 0, 0, 0)
                    update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 0)

                    order_number = sell_order_number
                    type_order = 'Sell'
                    type_global_order = 'Market'
                    type_flag = 'sell_all'
                    rate_plan_order = p0
                    rate_order = p0
                    amount_count_order = K_count_coin_action
                    total_amount_order = amount_count_order * rate_order
                    insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                   rate_plan_order, rate_order, amount_count_order, total_amount_order)

                    t_step_action = t
                    id_order_buy_open = 1
                    id_order_sell_loss_open = 1
                    status_bot = 'In work'
                    date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     't_step_action': t_step_action,
                                                     'id_order_buy_open': buy_order_number,
                                                     'id_order_sell_loss_open': id_order_sell_loss_open,
                                                     'status_bot': status_bot,
                                                     'date_wait_bot': date_wait_bot
                                                 }})

                    order_status = 0
                    while order_status < 1:
                        time.sleep(time_sleep_check_result_bot)
                        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        date_wait_action = date_wait_bot

                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {'date_wait_bot': date_wait_bot}})

                        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                        {'$set': {'date_wait_action': date_wait_action}})

                        list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)

                        if sell_order_number not in list_open_order_number:
                            update_db_order_result(market_place, id_bot, sell_order_number)
                            id_result_action = calculation_new_action(id_bot, sell_order_number, t)
                            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                            {'$set': {'status_action': 'Complete'}})

                            DB_bot_collection.update_one({'id_bot': id_bot},
                                                         {'$set': {
                                                             'status_bot': 'Stop by DB stop_bot = 1',
                                                             'id_action_open': 0
                                                         }})
                            print_telegram('Bot {} stopped!'.format(id_bot))
                            order_status = 1
                            sys.exit()

                        else:
                            pass

            else:
                #         type_flag == 'sell_all'
                t = -1
                DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                {'$set': {'status_action': 'Complete'}})

                if find_one_in_db_bot['stop_bot'] == 1:
                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     'status_bot': 'Stop by DB stop_bot = 1',
                                                     'id_action_open': 0
                                                 }})
                    print_telegram('Bot {} stopped!'.format(id_bot))
                    sys.exit()
                else:
                    pass

        # -------------------------------------------------------------------------------------------------

        else:
            if t < len(S_amounts) - 1:
                if buy_order_number not in list_open_order_number:

                    update_db_order_result(market_place, id_bot, buy_order_number)

                    # скасування попереднього ордеру sell
                    find_one_in_db_orders = DB_orders_collection.find_one({'id_bot': id_bot,
                                                                           'order_number': sell_order_number})
                    if find_one_in_db_orders['status_order'] == 'Open':
                        api_order_cancel(id_bot, market_place, sell_order_number)
                        update_db_order_cancel(id_bot, sell_order_number)
                    else:
                        pass

                    t = t + 1
                    p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')

                    buy_result_action = calculation_new_action(id_bot, buy_order_number, t)
                    id_result_action = buy_result_action[0]
                    number = buy_result_action[-1]
                    find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot,
                                                                           'id_action': id_result_action})
                    K_count_coin_action = find_one_in_db_action['K_count_coin_action']
                    P_price_action = find_one_in_db_action['P_price_action']

                    if t < len(S_amounts) - 1:
                        # параметри для ордеру buy
                        p_buy = p0 * (1 - procent[t + 1])
                        k0 = number[t + 1]
                        update_buy_part_in_db_action(id_bot, id_result_action, p_buy, k0, number)

                        buy_order_number = api_buy_limit(id_bot, market_place, currency_pair, coin, coin_base, p_buy,
                                                         k0)

                        update_buy_number_to_all(id_bot, id_result_action, buy_order_number)

                        order_number = buy_order_number
                        type_order = 'Buy'
                        type_global_order = 'Limit'
                        type_flag = 'buy_all'
                        rate_plan_order = p_buy
                        rate_order = p_buy
                        amount_count_order = k0
                        total_amount_order = rate_order * amount_count_order
                        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                       rate_plan_order, rate_order, amount_count_order,
                                                       total_amount_order)

                        # параметри для нового ордеру sell
                        p_sell = P_price_action * (1 + r_fin / 100)
                        amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
                        limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                                     min_total_amount_in_order_calculation(market_place, coin_base) /
                                                     (p_sell * 1.05))
                        if amount_sell > limit_amount_for_order:
                            type_flag = 'sell_part'
                        else:
                            amount_sell = K_count_coin_action
                            type_flag = 'sell_all'

                        update_sell_part_in_db_action(id_bot, id_result_action, p_sell, amount_sell)

                        sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base,
                                                           p_sell, amount_sell)

                        update_sell_number_to_all(id_bot, id_result_action, sell_order_number)

                        order_number = sell_order_number
                        type_order = 'Sell'
                        type_global_order = 'Limit'
                        rate_plan_order = p_sell
                        rate_order = p_sell
                        amount_count_order = amount_sell
                        total_amount_order = rate_order * amount_count_order
                        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                       rate_plan_order, rate_order, amount_count_order,
                                                       total_amount_order)

                        update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 0)

                        t_step_action = t
                        id_order_sell_loss_open = 0
                        status_bot = 'In work'
                        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {
                                                         't_step_action': t_step_action,
                                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                                         'status_bot': status_bot,
                                                         'date_wait_bot': date_wait_bot
                                                     }})

                    else:

                        p_sell = P_price_action * (1 + r_fin / 100)
                        amount_sell = K_count_coin_action - (S_amounts[0] / p_sell)
                        limit_amount_for_order = max(min_amount_in_order_calculation(market_place, coin),
                                                     min_total_amount_in_order_calculation(market_place, coin_base) /
                                                     (p_sell * 1.05))
                        if amount_sell > limit_amount_for_order:
                            type_flag = 'sell_part'
                        else:
                            amount_sell = K_count_coin_action
                            type_flag = 'sell_all'

                        update_sell_part_in_db_action(id_bot, id_result_action, p_sell, amount_sell)

                        sell_order_number = api_sell_limit(id_bot, market_place, currency_pair, coin, coin_base,
                                                           p_sell, amount_sell)

                        update_sell_number_to_all(id_bot, id_result_action, sell_order_number)

                        update_buy_part_in_db_action(id_bot, id_result_action, 0, 0, 0)

                        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                        {'$set': {'buy_order_number_action': 1}})

                        order_number = sell_order_number
                        type_order = 'Sell'
                        type_global_order = 'Limit'
                        rate_plan_order = p_sell
                        rate_order = p_sell
                        amount_count_order = amount_sell
                        total_amount_order = amount_count_order * rate_order
                        insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                       rate_plan_order, rate_order, amount_count_order,
                                                       total_amount_order)

                        p_loss = p0 * (1 - procent_loss / 100)

                        update_sell_loss_in_db_action(id_bot, id_result_action, p_loss, K_count_coin_action, 1)
                        #  виставлення stoploss
                        t_step_action = t
                        id_order_buy_open = 1
                        id_order_sell_loss_open = 1
                        status_bot = 'In work'
                        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {
                                                         't_step_action': t_step_action,
                                                         'id_order_buy_open': buy_order_number,
                                                         'id_order_sell_loss_open': id_order_sell_loss_open,
                                                         'status_bot': status_bot,
                                                         'date_wait_bot': date_wait_bot
                                                     }})

                else:
                    pass

            else:
                # момент stoploss
                p0 = api_ticker_price_by_type(id_bot, market_place, currency_pair, 'bid')
                # list_open_order_number = numbers_open_orders(currency_pair)
                id_action_open = DB_bot_collection.find_one({'id_bot': id_bot})['id_action_open']
                p_loss = DB_action_collection.find_one({'id_bot': id_bot,
                                                        'id_action': id_action_open})['sell_loss_price_action']

                if p0 <= p_loss:
                    p_sell_loss = p0
                    # скасування попереднього ордеру sell
                    find_one_in_db_orders = DB_orders_collection.find_one({'id_bot': id_bot,
                                                                           'order_number': sell_order_number})
                    if find_one_in_db_orders['status_order'] == 'Open':
                        api_order_cancel(id_bot, market_place, sell_order_number)
                        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                                        {'$set': {'restart_type_action': [1, 1, 0]}})
                        update_db_order_cancel(id_bot, sell_order_number)
                    else:
                        pass

                    find_one_in_db_action = DB_action_collection.find_one({'id_bot': id_bot,
                                                                           'id_action': id_action_open})
                    K_count_coin_stoploss = find_one_in_db_action['K_count_coin_action']

                    # обміркувати цей момент, бо лише сповіщення в телеграм мало для подальших дій
                    existing_count_coin_on_balance = api_balance_coin(id_bot, market_place, coin)
                    if existing_count_coin_on_balance < K_count_coin_stoploss:
                        K_count_coin_stoploss = existing_count_coin_on_balance
                        print_telegram('WARRNING existing_count_coin_on_balance < K_count_coin_stoploss!!!')
                    else:
                        pass

                    sell_loss_order_number = api_sell_market(id_bot, market_place, currency_pair, coin, coin_base,
                                                             p_sell_loss, K_count_coin_stoploss)

                    update_sell_loss_number_to_all(id_bot, id_action_open, sell_loss_order_number)

                    order_number = sell_loss_order_number
                    type_order = 'Sell_loss'
                    type_global_order = 'Limit'
                    type_flag = 'sell_all'
                    rate_plan_order = p0
                    rate_order = p_sell_loss
                    amount_count_order = K_count_coin_stoploss
                    total_amount_order = rate_order * amount_count_order
                    insert_first_part_of_db_orders(id_bot, order_number, type_order, type_global_order, type_flag,
                                                   rate_plan_order, rate_order, amount_count_order, total_amount_order)
                    t_step_action = t
                    id_order_sell_open = 1
                    id_order_buy_open = 1
                    status_bot = 'In work'
                    date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    DB_bot_collection.update_one({'id_bot': id_bot},
                                                 {'$set': {
                                                     't_step_action': t,
                                                     'id_order_sell_open': id_order_sell_open,
                                                     'id_order_buy_open': id_order_buy_open,
                                                     'status_bot': status_bot,
                                                     'date_wait_bot': date_wait_bot
                                                 }})

                    index_stoploss = 0
                    while index_stoploss < 1:
                        time.sleep(time_sleep_steps_bot)

                        date_wait_bot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        date_wait_action = date_wait_bot

                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {'date_wait_bot': date_wait_bot}})

                        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_action_open},
                                                        {'$set': {'date_wait_action': date_wait_action}})

                        list_open_order_number = api_list_of_open_orders(id_bot, market_place, currency_pair)
                        find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': id_bot})
                        sell_loss_order_number = find_one_in_db_bot['id_order_sell_loss_open']

                        if sell_loss_order_number not in list_open_order_number:
                            t = -1
                            update_db_order_result(market_place, id_bot, sell_loss_order_number)
                            id_result_action = calculation_new_action(id_bot, sell_loss_order_number, t)

                            index_stoploss = 1
                            step = DB_bot_collection.find_one({'id_bot': id_bot})['step']
                            step = step + 1
                            # оновити значення полів для sell і sell_order_number
                            update_sell_part_in_db_action(id_bot, id_result_action, 0, 0)
                            DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                            {'$set': {'sell_order_number_action': 1}})
                            # оновлений запис в базі action про стан loss
                            update_sell_loss_in_db_action(id_bot, id_result_action, 0, 0, 1)

                            # в базі bot оновлюємо запис про актуальний стан action
                            DB_bot_collection.update_one({'id_bot': id_bot},
                                                         {'$set': {
                                                             'id_order_sell_open': 1,
                                                             'id_order_sell_loss_open': 1,
                                                             'step': step
                                                         }})

                        else:
                            pass

                    if DB_bot_collection.find_one({'id_bot': id_bot})['stop_bot'] == 1:
                        DB_action_collection.update_one({'id_bot': id_bot, 'id_action': id_result_action},
                                                        {'$set': {'status_action': 'Complete'}})

                        DB_bot_collection.update_one({'id_bot': id_bot},
                                                     {'$set': {
                                                         'status_bot': 'Stop by DB stop_bot = 1',
                                                         'id_action_open': 0
                                                     }})
                        print_telegram('Bot {} stopped!'.format(id_bot))
                        sys.exit()
                    else:
                        pass

                else:
                    pass
