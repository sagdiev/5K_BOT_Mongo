from poloniex import Poloniex
from subprocess import Popen, PIPE
from pymongo import MongoClient
import logging
import telebot
import datetime
import psutil
import signal
import time
import os

minutes = 5
minutes_restart = 5

logging.basicConfig(filename='Restart_BigBOTT.log', level=logging.INFO, filemode='w')

polo = Poloniex()

client = MongoClient('127.0.0.1', 27017)

db = client.DB_bigbott
DB_action_collection = db.DB_action
DB_bot_collection = db.DB_bot
DB_orders_collection = db.DB_orders
DB_log_restart_collection = db.DB_log_restart
DB_telebot_collection = db.DB_telebot
DB_users = db.DB_users


def print_telegram(user_id, text_mess):
    # відправляє повідомлення для множини ботів, що вказані у списку "власника"
    find_one_in_db_user = DB_users.find_one({'id_user': user_id})
    admin_token = DB_users.find_one({'id_user': 0})['token_telegram']
    bot_admin = telebot.TeleBot(admin_token)
    token = find_one_in_db_user['token_telegram']
    bot_def = telebot.TeleBot(token)

    text_admin = 'User {}. \n{} '.format(user_id, text_mess)
    bot_admin.send_message(DB_users.find_one({'id_user': 0})['id_telegram'][0], text_admin)

    for id_telegram in find_one_in_db_user['id_telegram']:
        try:
            bot_def.send_message(id_telegram, text_mess)
        except:
            logging.info('-' * 50)
            logging.info(mes)


def get_users_list():
    users_list = []
    for _ in DB_users.find():
        if _['status_user'].lower() == 'active':
            users_list.append(_['id_user'])

    return users_list


def get_all_id_bots(user_id):
    # повертає список id усіх ботів, що є в базі DB_bot
    list_id_bots = []
    for _ in DB_bot_collection.find({'id_user': user_id}):
        list_id_bots.append(_['id_bot'])
    DB_users.update_one({'id_user': user_id}, {'$set': {'list_bots': list_id_bots}})

    return list_id_bots


def get_all_id_bots_in_work(user_id):
    # повертає список "працюючих" ботів для "власника"
    id_bots_in_work = []
    for _ in DB_bot_collection.find({'id_user': user_id}):
        if _['status_bot'] == 'In work':
            id_bots_in_work.append(_['id_bot'])
        else:
            pass

    return id_bots_in_work


def list_warning_bots(user_id):
    global minutes
    warning_bots_list_def = []
    time_check = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
    for _ in DB_bot_collection.find({'id_user': user_id, 'status_bot': 'In work'}):

        if datetime.datetime.strptime(_['date_wait_bot'], "%Y-%m-%d %H:%M:%S") < time_check:
            warning_bots_list_def.append(_['id_bot'])

    return warning_bots_list_def


def get_id_open_actions(user_id):
    id_actions_in_work = []
    for _ in DB_bot_collection.find({'id_user': user_id}):
        if _['status_bot'] == 'In work':
            id_actions_in_work.append(_['id_action_open'])
        else:
            pass

    return id_actions_in_work


def statistics_bots_for_user(user_id):
    # загальна статистика ботів одного user
    sum_invest_in_usdt = 0
    profit_in_usdt = 0
    list_all_id_bots_in_work = get_all_id_bots_in_work(user_id)
    if len(list_all_id_bots_in_work) == 0:
        pass
    else:
        for _ in list_all_id_bots_in_work:
            find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': _})
            coin_base = find_one_in_db_bot_def['coin_base']
            profit_bot = find_one_in_db_bot_def['profit_bot']
            # id_action_def = find_one_in_db_bot_def['id_action_open']

            if coin_base in ['BTC', 'XBT']:
                try:
                    price_usdt = polo.returnTicker()['USDT_BTC']['last']
                except:
                    price_usdt = 7000

            elif coin_base == 'ETH':
                try:
                    price_usdt = polo.returnTicker()['USDT_ETH']['last']
                except:
                    price_usdt = 700
            else:
                price_usdt = 1

            profit_in_usdt = profit_in_usdt + round(profit_bot * price_usdt, 2)
            sum_invest_in_usdt = sum_invest_in_usdt + round(sum(find_one_in_db_bot_def['S_amounts']) * price_usdt, 2)

        profit_percent = round(((profit_in_usdt / sum_invest_in_usdt) * 100), 2)

        DB_users.update_one({'id_user': user_id},
                            {'$set': {
                                'invest_sum_in_usdt': sum_invest_in_usdt,
                                'profit_in_usdt': profit_in_usdt,
                                'profit_percent_in_usdt': profit_percent
                            }})


def review_active_pid_bot(bot_id):
    list_pid_bot_def = DB_bot_collection.find_one({'id_bot': bot_id})['PID_list']
    pid_bot_def = list_pid_bot_def[0]
    pid_process_bot = list_pid_bot_def[1]
    pid_next_process_def = list_pid_bot_def[-1]
    # print('active bot ', bot_id, 'list_pid_bot_def = ', list_pid_bot_def)

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
    # перезапускає ботів, що впали.
    global minutes_restart
    for id_bot_from_warning in list_id_bots_warning_def:
        find_one_in_db_bot_def = DB_bot_collection.find_one({'id_bot': id_bot_from_warning})
        list_pid_bot = find_one_in_db_bot_def['PID_list']
        time_last_restart = datetime.datetime.strptime(find_one_in_db_bot_def['date_last_restart'],
                                                       "%Y-%m-%d %H:%M:%S")

        if time_last_restart < (datetime.datetime.now() - datetime.timedelta(minutes=minutes_restart)) or step == 0:
            review_active_pid_bot(id_bot_from_warning)

            process = Popen(find_one_in_db_bot_def['path_bot'], shell=True, close_fds=True, stdout=PIPE)
            pid_process = process.pid
            list_pid_bot[1] = pid_process
            list_pid_bot[-1] = pid_process + 1

            DB_bot_collection.update_one({'id_bot': id_bot_from_warning},
                                         {'$set': {
                                             'PID_list': list_pid_bot,
                                             'date_last_restart': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                         }})
            # print('Restart id = {}, list_pid_bot = {}'.format(id_bot_from_warning, list_pid_bot))
            logging.info('Restart id = {}, list_pid_bot = {}'.format(id_bot_from_warning, list_pid_bot))
        else:
            # print('Waiting for finishing restart id = {}, list_pid_bot = {}'.format(id_bot_from_warning,
            # list_pid_bot))
            logging.info('Waiting for finishing restart id = {}, list_pid_bot = {}'.format(id_bot_from_warning,
                                                                                           list_pid_bot))

        time.sleep(45)


def send_notification(user_id):
    find_one_in_db_users_def = DB_users.find_one({'id_user': user_id})
    date_wait = datetime.datetime.strptime(find_one_in_db_users_def['next_notification'], "%Y-%m-%d %H:%M:%S")
    if datetime.datetime.now() > date_wait:
        hour = find_one_in_db_users_def['frequency_notification']
        mes_def = get_messages(get_all_id_bots_in_work(user_id), list_warning_bots(user_id))
        mes_def = '{} statistics \n\n{}'.format('Hour' if hour == 1 else 'Hours', mes_def)
        print_telegram(user_id, mes_def)
        next_notification_def = (datetime.datetime.now() + datetime.timedelta(hours=hour)).strftime("%Y-%m-%d %H:%M:%S")
        DB_users.update_one({'id_user': user_id}, {'$set': {'next_notification': next_notification_def}})
    else:
        pass


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
            try:
                price_usdt = polo.returnTicker()['USDT_BTC']['last']
            except:
                price_usdt = 7000
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)
        elif coin_base == 'ETH':
            try:
                price_usdt = polo.returnTicker()['USDT_ETH']['last']
            except:
                price_usdt = 700
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)
        else:
            price_usdt = 1
            profit_bot_usd = round(price_usdt * find_one_in_db_bot_def['profit_bot'], 2)

        sum_invest_in_usd = round(sum(find_one_in_db_bot_def['S_amounts']) * price_usdt, 0)
        profit_bot_percent = round((profit_bot_usd / sum_invest_in_usd) * 100, 2)

        total_invest_in_usd = round(total_invest_in_usd + sum_invest_in_usd, 2)
        total_profit_in_usd = round(total_profit_in_usd + profit_bot_usd, 2)
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


for user in get_users_list():
    next_notification = (datetime.datetime.now() + datetime.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    DB_users.update_one({'id_user': user},
                        {'$set': {
                            'list_bots': get_all_id_bots(user),
                            'list_id_open_action_currently': get_id_open_actions(user),
                            'list_working_bot_currently': get_all_id_bots_in_work(user),
                            'next_notification': next_notification
                        }})

step = 0

while True:

    for id_user in get_users_list():
        # оновлюю статистику ботів юзера
        statistics_bots_for_user(id_user)

        find_one_in_db_users = DB_users.find_one({'id_user': id_user})
        previous_id_open_actions = find_one_in_db_users['list_id_open_action_currently']
        list_id_open_action = get_id_open_actions(id_user)

        # перевірка чи відбувся новий action
        new_action = list(set(previous_id_open_actions + list_id_open_action) - set(previous_id_open_actions))
        if len(new_action) == 0:
            pass
        else:
            mes = ''
            for action in new_action:
                find_one_in_db_action = DB_action_collection.find_one({'id_action': action})
                if find_one_in_db_action['t_steps_action'] == 0:
                    mes = mes + 'bot {} from step {} to {}. \nProfit action {}.'. \
                        format(find_one_in_db_action['id_bot'], find_one_in_db_action['t_step_previous'],
                               find_one_in_db_action['t_steps_action'], find_one_in_db_action['profit_action'])
                else:
                    mes = mes + 'bot {} from step {} to {}. \n'.format(find_one_in_db_action['id_bot'],
                                                                       find_one_in_db_action['t_step_previous'],
                                                                       find_one_in_db_action['t_steps_action'])
            mes = 'New action:\n\n' + mes
            print_telegram(id_user, mes)

        DB_users.update_one({'id_user': id_user}, {'$set': {'list_id_open_action_currently': list_id_open_action}})

        # перевірка чи додався новий бот
        previous_working_bots = find_one_in_db_users['list_working_bot_currently']
        list_working_bots = get_all_id_bots_in_work(id_user)

        new_working_bots = list(set(previous_working_bots + list_working_bots) - set(previous_working_bots))
        if len(new_working_bots) == 0:
            pass
        else:
            mes = 'You have {} new {} in work.'.format(len(new_working_bots),
                                                       'bot' if len(new_working_bots) == 1 else 'bots')
            print_telegram(id_user, mes)

        # перевірка чи "зникли" деякі боти
        new_lost_bots = list(set(previous_working_bots + list_working_bots) - set(list_working_bots))
        if len(new_lost_bots) == 0:
            pass
        else:
            mes = 'You lost {} {}.'.format(len(new_lost_bots), 'bot' if len(new_lost_bots) == 1 else 'bots')
            print_telegram(id_user, mes)

        DB_users.update_one({'id_user': id_user}, {'$set': {'list_working_bot_currently': list_working_bots}})

        # якщо боти якогось юзера 'зламалися', то запустити їх знову
        warning_bots_list = list_warning_bots(id_user)

        if len(warning_bots_list) == 0:
            pass
        else:
            # print('\nuser {}. Time = {}. \nWarning_bots_list = {}'.format(id_user, time.ctime(), warning_bots_list))
            logging.info('\nuser {}. Time = {}. \nWarning_bots_list = {}'.format(id_user, time.ctime(),
                                                                                 warning_bots_list))

            restart_bots(warning_bots_list)

        send_notification(id_user)

    step = 1

    time.sleep(60 * minutes)
