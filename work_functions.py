# from poloniex import Poloniex
# from binance.client import Client
# from bittrex.bittrex import *
# import krakenex
# from pymongo import MongoClient
from main import *
import time
import datetime
import sys

# import pandas as pd

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


def log_api_insert_in_db(bot_id, type_api_def, description_def):
    if db_log_api.find({'id_bot': bot_id}).count() == 0:
        new_id_log_api = 1
    else:
        last_record_in_db_log = db_log_api.find({'id_bot': bot_id}).count() - 1
        new_id_log_api = db_log_api.find({'id_bot': bot_id})[last_record_in_db_log]['id_log_api'] + 1

    db_log_api.insert_one({'id_log_api': new_id_log_api,
                           'id_bot': bot_id,
                           'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           'type_api': type_api_def,
                           'description': description_def,
                           'trigger': 1})
    DB_bot_collection.update_one({'id_bot': bot_id}, {'$set': {'id_log_api_last': new_id_log_api}})

    return new_id_log_api


def log_api_trigger_update_db(bot_id, id_log_api_def):
    # db_log_api.find_one({'id_bot': bot_id, 'id_log_api': id_log_api_def})['trigger'] = 0
    db_log_api.delete_one({'id_bot': bot_id, 'id_log_api': id_log_api_def})

# def_API


def api_list_of_open_orders(bot_id, market_place_def, currency_pair_def):
    # log_description = str(market_place_def) + ' API Return Open orders (' + str(currency_pair_def) + \
    #                   ') in def api_list_of_open_orders'
    # id_log_api_current = log_api_insert_in_db(bot_id, 'API Return open Orders', log_description)
    list_open_order_number_def = []

    count_attempt = 0
    while count_attempt < 5:

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

            count_attempt = 5
            # log_api_trigger_update_db(bot_id, id_log_api_current)

        except:
            count_attempt = count_attempt + 1
            if db_log_api.find({'id_bot': bot_id}).count() == 0:
                new_id_log_api = 1
            else:
                new_id_log_api = db_log_api.find()[db_log_api.find({'id_bot': bot_id}).count() - 1]['id_log_api'] + 1

            if count_attempt == 5:
                description_value = 'Stop and Restart after Ping by try. Attempt = ' + str(count_attempt)
                db_log_api.insert_one({'id_log_api': new_id_log_api,
                                       'id_bot': bot_id,
                                       'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                       'type_api': 'API Return open Orders',
                                       'description': description_value,
                                       'trigger': 1
                                       })
                # log_api_trigger_update_db(bot_id, id_log_api_current)
                sys.exit()

            else:
                description_value = 'Ping by try. Attempt = ' + str(count_attempt)
                db_log_api.insert_one({'id_log_api': new_id_log_api,
                                       'id_bot': bot_id,
                                       'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                       'type_api': 'API Return open Orders',
                                       'description': description_value,
                                       'trigger': 0
                                       })
                time.sleep(1)

    return list_open_order_number_def


def api_balance_coin(bot_id, market_place_def, coin_def):
    log_description = str(market_place_def) + ' API Return Balance (' + str(coin_def) + \
                      ') in def api_balance_coin'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Return Balance', log_description)

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

    log_api_trigger_update_db(bot_id, id_log_api_current)

    return api_balance_coin_calc


def api_ticker_price_by_type(bot_id, market_place_def, coin_pair_def, type_of_price_def):
    log_description = str(market_place_def) + ' API Return Ticker Price (' + str(coin_pair_def) + \
                      ') in def api_ticker_price_by_type'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Return Ticker Price', log_description)
    api_ticker_price_calc = -1

    count_attempt = 0
    while count_attempt < 5:
        try:
            time.sleep(0.5)
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

            count_attempt = 5

        except Exception:
            count_attempt = count_attempt + 1

    log_api_trigger_update_db(bot_id, id_log_api_current)

    return api_ticker_price_calc


def api_order_cancel(bot_id, market_place_def, order_number_def):
    log_description = str(market_place_def) + ' API Order Cancel (' + str(order_number_def) + \
                      ') in def api_order_cancel'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Cancel ', log_description)

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

    log_api_trigger_update_db(bot_id, id_log_api_current)


def api_sell_limit(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_def, amount_sell_def):
    log_description = str(market_place_def) + ' API Order Open Sell Limit (sell ' + str(coin_def) + ' - base ' + \
                      str(coin_base_def) + ') in def api_sell_limit'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Open Sell Limit', log_description)

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
        sell_order_number_calc = -1

    log_api_trigger_update_db(bot_id, id_log_api_current)

    return sell_order_number_calc


def api_sell_market(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_plan_def,
                    amount_sell_def):
    log_description = str(market_place_def) + ' API Order Open Sell Market (sell ' + str(coin_def) + ' - base ' + \
                      str(coin_base_def) + ') in def api_sell_market'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Open Sell Market', log_description)

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
        api_sell_limit_calc = my_bittrex.sell_limit(currency_pair_def, amount_to_sell_calc, rate_emulation_sell_calc)
        sell_order_number_calc = api_sell_limit_calc['result']['uuid']
    else:
        print('Unknown market API !')
        sell_order_number_calc = -1

    log_api_trigger_update_db(bot_id, id_log_api_current)

    return sell_order_number_calc


def api_buy_limit(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_def, amount_buy_def):
    log_description = str(market_place_def) + ' API Order Open Buy Limit (buy ' + str(coin_def) + ' - base ' + \
                      str(coin_base_def) + ') in def api_buy_limit'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Open Buy Limit', log_description)

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
        buy_order_number_calc = -1

    log_api_trigger_update_db(bot_id, id_log_api_current)

    return buy_order_number_calc


def api_buy_market(bot_id, market_place_def, currency_pair_def, coin_def, coin_base_def, rate_plan_def, amount_buy_def):
    log_description = str(market_place_def) + ' API Order Open Buy Market (buy ' + str(coin_def) + ' - base ' + \
                      str(coin_base_def) + ') in def api_buy_market'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Open Buy Market', log_description)

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
        api_buy_limlit_calc = my_bittrex.buy_limit(currency_pair_def, amount_to_buy_calc, rate_emulation_buy_calc)
        buy_order_number_calc = api_buy_limlit_calc['result']['uuid']
    else:
        print('Unknown market API !')
        buy_order_number_calc = -1

    log_api_trigger_update_db(bot_id, id_log_api_current)

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


# Руслан, надо обсудить: возможно def amount_to_buy_by_quota_calculation нужно вставить во все api_buy
# при зустрічі або завтра по телефону, але я за, щоб усе в одну функцію усе звести


def min_total_amount_in_order_calculation(market_place_def, coin_base_def):
    if market_place_def == 'Poloniex':
        if coin_base_def == 'BTC':
            min_total_amount_calc = 0.0001
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.0001
        else:
            min_total_amount_calc = 1

    elif market_place_def == 'Binance':
        if coin_base_def == 'BTC':
            min_total_amount_calc = 0.001
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.01
        else:
            min_total_amount_calc = 10

    elif market_place_def == 'Kraken':
        # XBT == BTC
        if coin_base_def in ['XBT', 'BCH']:
            min_total_amount_calc = 0.002
        elif coin_base_def == 'ETH':
            min_total_amount_calc = 0.02
        elif coin_base_def in ['XMR', 'LTC', 'MLN']:
            min_total_amount_calc = 0.1
        else:
            min_total_amount_calc = 0.001
    elif market_place_def == 'Bittrex':
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
        if coin_def == 'BTC':
            min_amount_calc = 0.0001
        elif coin_def == 'ETH':
            min_amount_calc = 0.0001
        else:
            min_amount_calc = 0.0001

    elif market_place_def == 'Binance':
        if coin_def == 'BTC':
            min_amount_calc = 0.001
        elif coin_def == 'ETH':
            min_amount_calc = 0.01
        else:
            min_amount_calc = 0.001

    elif market_place_def == 'Kraken':
        # XBT == BTC
        if coin_def in ['XBT', 'BCH']:
            min_amount_calc = 0.002
        elif coin_def == 'ETH':
            min_amount_calc = 0.02
        elif coin_def in ['XMR', 'LTC', 'MLN']:
            min_amount_calc = 0.1
        else:
            min_amount_calc = 0.002
    elif market_place_def == 'Bittrex':
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
                         date_wait_bot_def, step_def, path_bot_def):
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
        'path_bot': path_bot_def
    })


def insert_first_part_of_db_action(id_action_previous_def, bot_id, t_step_previous_def, t_steps_action,
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

    s_amounts_def = DB_bot_collection.find_one({'id_bot': bot_id})['S_amounts']

    if t_steps_action == -1:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [1, 0, 1],
                                                  'sell_order_number_action': 1}})
    elif 0 <= t_steps_action < len(s_amounts_def) - 1:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [0, 0, 1]}})
    else:
        DB_action_collection.update_one({'id_bot': bot_id, 'id_action': new_id_action},
                                        {'$set': {'restart_type_action': [0, 1, 0]}})

    return new_id_action


def calculation_new_action(bot_id, order_number_def, t_def):
    type_order_def = DB_orders_collection.find_one({'id_bot': bot_id, 'order_number': order_number_def})['type_order']
    currency_pair_def = DB_bot_collection.find_one({'id_bot': bot_id})['coin_pair_bot']
    market_place_def = DB_bot_collection.find_one({'id_bot': bot_id})['market_place_bot']
    p0_def = api_ticker_price_by_type(bot_id, market_place_def, currency_pair_def, 'bid')

    order_parent_action_def = order_number_def
    find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
    id_action_previous_def = find_one_in_db_bot_def['id_action_open']
    find_one_in_db_orders_def = DB_orders_collection.find_one({'id_bot': bot_id,
                                                               'order_number': order_parent_action_def})
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

        price_p0_action_def = p0_def

        c_amount_action_def = price_action_def * k_count_coin_action_previous_def - result_total_order_previous
        k_count_coin_action_def = k_count_coin_action_previous_def - result_amount_coin_order_previous
        b_amount_action_def = price_action_def * k_count_coin_action_def
        p_price_action_def = c_amount_action_def / k_count_coin_action_def
        profit_action_def = result_total_order_previous - c_amount_action_previous_def + c_amount_action_def
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

    id_result_action_def = insert_first_part_of_db_action(id_action_previous_def, bot_id, t_step_previous_def, t_def,
                                                          order_parent_action_def, price_p0_action_def,
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


def insert_first_part_of_db_orders(bot_id, order_number_def, type_order_def, type_global_order_def, rate_plan_order_def,
                                   rate_order_def, amount_coin_order_def, total_amount_order_def):
    new_id_order = DB_orders_collection.count() + 1
    date_record_action = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    coin_pair = DB_bot_collection.find_one({'id_bot': bot_id})['coin_pair_bot']
    DB_orders_collection.insert_one({
        'id_order': new_id_order,
        'id_bot': bot_id,
        'order_number': order_number_def,
        'date_order': date_record_action,
        'coin_pair_order': coin_pair,
        'type_order': type_order_def,
        'type_global_order': type_global_order_def,
        'rate_plan_order': rate_plan_order_def,
        'rate_order': rate_order_def,
        'amount_coin_order': amount_coin_order_def,
        'total_amount_order': total_amount_order_def,
        'status_order': 'Open'})
    return new_id_order


def update_db_order_result(market_place_def, bot_id, order_number_def):
    log_description = str(market_place_def) + ' API Order Trade History (' + str(order_number_def) + \
                      ') in def update_db_order_result'
    id_log_api_current = log_api_insert_in_db(bot_id, 'API Order Trade History', log_description)

    cursor = DB_orders_collection.find_one({'id_bot': bot_id, 'order_number': order_number_def})
    amount_coin_order_def = cursor['amount_coin_order']
    total_amount_order_def = cursor['total_amount_order']

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
        list_trades_id = []
        for _ in range(len(list_result)):
            all_amount = all_amount + float(list_result[_]['qty'])
            all_total = all_total + float(list_result[_]['price']) * float(list_result[_]['qty'])
            list_trades_id.append(list_result[_]['id'])

        result_rate_order = all_total / all_amount

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

    # Руслан, на написал случай 'Bittrex' - проверяй
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
        for _ in range(len(list_result)):
            all_amount = all_amount + float(list_result[_]['Quantity'])
            all_total = all_total + float(list_result[_]['Price'])
            list_trades_id.append(list_result[_]['OrderUuid'])
            product_price_amount = product_price_amount + list_result[_]['Quantity'] * list_result[_]['PricePerUnit']

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

    log_api_trigger_update_db(bot_id, id_log_api_current)


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
