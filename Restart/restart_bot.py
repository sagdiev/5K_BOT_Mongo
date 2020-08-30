from poloniex import Poloniex
import os
import psutil
from subprocess import Popen, PIPE
import Restart.constants as constants
import telebot
import time
import datetime
from pymongo import MongoClient
import signal

api_key = constants.APIKey_2
api_secret = constants.Secret_2

token = constants.token
set_id = constants.set_id

token_2_alex = constants.token_2_alex
set_id_2_alex = constants.set_id_2_alex


polo = Poloniex(api_key, api_secret)

bot = telebot.TeleBot(token)
bot_2_alex = telebot.TeleBot(token_2_alex)

client = MongoClient('127.0.0.1', 27017)

db = client.DB_bigbott
DB_action_collection = db.DB_action
DB_bot_collection = db.DB_bot
DB_orders_collection = db.DB_orders
DB_log_restart_collection = db.DB_log_restart
DB_telebot_collection = db.DB_telebot


def print_telegram(text_mess):
    for _ in set_id:
        bot.send_message(_, text_mess)


def print_telegram_2_alex(text_mess):
    for _ in set_id_2_alex:
        bot_2_alex.send_message(_, text_mess)


def get_all_id_bots():
    list_id_bots = []
    for _ in DB_bot_collection.find():
        list_id_bots.append(_['id_bot'])
    return list_id_bots


def get_all_id_bots_in_work():
    id_bots_in_work = []
    for _ in DB_bot_collection.find():
        if _['status_bot'] == 'In work':
            id_bots_in_work.append(_['id_bot'])
        else:
            pass
    return id_bots_in_work


def get_all_id_actions_in_work():
    id_actions_in_work = []
    for _ in DB_bot_collection.find():
        if _['status_bot'] == 'In work':
            id_actions_in_work.append(_['id_action_open'])
        else:
            pass
    return id_actions_in_work


def review_active_pid_bot(bot_id):
    list_pid_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})['PID_list']
    pid_bot_def = list_pid_bot_def[0]
    pid_process_bot = list_pid_bot_def[1]
    pid_next_process_def = list_pid_bot_def[-1]
    print('active bot ', bot_id, 'list_pid_bot_def = ', list_pid_bot_def)

    pid_all_list = psutil.pids()
    if pid_bot_def in pid_all_list:
        os.kill(pid_bot_def, signal.SIGTERM)
    else:
        pass

    pid_all_list = psutil.pids()
    if pid_process_bot in pid_all_list:
        os.kill(pid_process_bot, signal.SIGTERM)
    else:
        pass

    pid_all_list = psutil.pids()
    if pid_next_process_def in pid_all_list:
        os.kill(pid_next_process_def, signal.SIGTERM)
    else:
        pass


def restart_bots(list_id_bots_warning_def):
    time_of_sleep_restart = 0.5
    for id_bot_from_warning in list_id_bots_warning_def:
        find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': id_bot_from_warning})
        list_pid_bot = find_one_in_db_bot_def['PID_list']

        review_active_pid_bot(id_bot_from_warning)

        process = Popen(find_one_in_db_bot_def['path_bot'], shell=True, close_fds=True, stdout=PIPE)
        pid_process = process.pid
        list_pid_bot[1] = pid_process
        list_pid_bot[-1] = pid_process + 1

        DB_bot_collection.update_one({'id_bot': id_bot_from_warning}, {'$set': {'PID_list': list_pid_bot}})

        print('Restart id = {}, list_pid_bot = {}'.format(id_bot_from_warning, list_pid_bot))

        time.sleep(time_of_sleep_restart)


def get_messages(list_id_bots_in_work_def, list_id_bots_warning_def):
    mes_def = ''
    total_invest_in_usd = 0
    total_profit_in_usd = 0
    total_profit_bot_percent = 0

    for bot_id in list_id_bots_in_work_def:
        find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})
        coin_base = find_one_in_db_bot_def['coin_base']
        market_place_bot = find_one_in_db_bot_def['market_place_bot']
        t_step_action = find_one_in_db_bot_def['t_step_action']
        coin_pair_bot = find_one_in_db_bot_def['coin_pair_bot']
        date_wait_bot = find_one_in_db_bot_def['date_wait_bot']

        if coin_base in ['BTC', 'XBT']:
            price_usdt = polo.returnTicker()['USDT_BTC']['last']
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)
        elif coin_base == 'ETH':
            price_usdt = polo.returnTicker()['USDT_ETH']['last']
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)
        else:
            price_usdt = 1
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)

        sum_invest_in_usd = round(sum(find_one_in_db_bot_def['S_amounts']) * price_usdt, 0)
        profit_bot_percent = round((profit_bot_usd / sum_invest_in_usd) * 100, 2)

        total_invest_in_usd = total_invest_in_usd + sum_invest_in_usd
        total_profit_in_usd = total_profit_in_usd + profit_bot_usd
        total_profit_bot_percent = round((total_profit_in_usd / total_invest_in_usd) * 100, 2)

        if bot_id in list_id_bots_warning_def:
            status_bot_def = 'WARNING! \n Stopped at {}'.format(date_wait_bot)
        else:
            status_bot_def = 'working'

        mes_def = mes_def + '\n' + '{} {} {} - {}\n     ' \
                                   't={}, Δ$={}, %={}, ΣS={}'.format(bot_id, market_place_bot, coin_pair_bot,
                                                                     status_bot_def, t_step_action, profit_bot_usd,
                                                                     profit_bot_percent, sum_invest_in_usd)

    mes_def = '\n' + mes_def + '\n\nTotal Δ = ${}, % {}, ΣS ${}'.format(total_profit_in_usd, total_profit_bot_percent,
                                                                        total_invest_in_usd)
    return mes_def


restart = 0
warning_score = 0
while True:

    list_id_bots_in_work_previous = []
    list_id_bots_warning_previous = []
    list_id_actions_in_work_previous = []

    t = 0
    time_of_sleep = 30
    time_repeat = 3600 / time_of_sleep

    while t < time_repeat:

        date_time_for_check = (datetime.datetime.now() - datetime.timedelta(seconds=70)).strftime("%Y-%m-%d %H:%M:%S")
        list_id_bots_in_work = get_all_id_bots_in_work()
        list_id_actions_in_work = get_all_id_actions_in_work()
        list_id_bots_warning = []

        mes = ''
        text_title = ''

        for i in list_id_bots_in_work:
            if i == 10:
                pass
            else:
                find_one_in_db_bot = DB_bot_collection.find_one({'id_bot': i})
                date_wait = find_one_in_db_bot['date_wait_bot']

                if date_wait <= date_time_for_check:
                    list_id_bots_warning.append(i)
                else:
                    pass
        if len(list_id_bots_warning) != 0:
            print('list_id_bots_warning =', list_id_bots_warning)
        else:
            pass

        set1 = len(set(list_id_bots_warning_previous + list_id_bots_warning) - set(list_id_bots_warning_previous))
        set2 = len(set(list_id_bots_warning_previous + list_id_bots_warning) - set(list_id_bots_warning))
        set3 = len(set(list_id_bots_in_work_previous + list_id_bots_in_work) - set(list_id_bots_in_work_previous))
        set4 = len(set(list_id_bots_in_work_previous + list_id_bots_in_work) - set(list_id_bots_in_work))
        set5 = len(set(list_id_actions_in_work_previous + list_id_actions_in_work) -
                   set(list_id_actions_in_work_previous))

        if set2 != 0:
            warning_score = 0
        else:
            pass

        if set1 != 0:
            warning_score = 0
        else:
            pass

        if (set1 + set2 + set3 + set4 + set5) != 0:

            if restart == 0 and set1 == 0:
                text_title = 'Restart Statistic BigBOTT'
                restart = 1
            elif restart == 0 and set1 != 0:
                text_title = 'Restart but WARNING! BigBOTT'
                warning_score = 1
                restart = 1
                restart_bots(list_id_bots_warning)
            elif set1 != 0 and warning_score == 0:
                text_title = 'WARNING NEW! BigBOTT'
                warning_score = 1
                restart_bots(list_id_bots_warning)
            elif set1 != 0 and warning_score == 1:
                text_title = 'Hour WARNING! BigBOTT'
            elif set2 != 0:
                text_title = 'Fixed some WARNING! BigBOTT'
            elif t == 0:
                text_title = 'Hour Statistic BigBOTT'
            elif set3 != 0:
                text_title = 'New Bot in Work BigBOTT'
            elif set4 != 0:
                text_title = 'Cancel Bot from Work BigBOTT'
            elif set5 != 0:
                text_title = 'New Action Statistic BigBOTT'
            else:
                text_title = 'Statistic BigBOTT'

            mes = text_title + get_messages(list_id_bots_in_work, list_id_bots_warning)
            print_telegram(mes)
            print_telegram_2_alex(mes)

        else:
            pass

        list_id_bots_in_work_previous = list_id_bots_in_work
        list_id_bots_warning_previous = list_id_bots_warning
        list_id_actions_in_work_previous = list_id_actions_in_work

        t = t + 1
        date_record_telebot = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        DB_telebot_collection.update_one({'id_telebot': 1},
                                         {'$set': {'date_wait_telebot': date_record_telebot}})

        time.sleep(time_of_sleep)

    restart = 1
