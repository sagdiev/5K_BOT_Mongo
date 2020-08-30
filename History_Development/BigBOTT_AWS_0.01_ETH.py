from poloniex import Poloniex
import time
import telebot
import sys
import math as m

api_key = 'EL0TITIV-8WZWI50B-1BA3JLA2-CFIJ4B79'
api_secret = 'e0da9dc02e1fa082afa9f4fc4a2c62e55c58c5b669c07e3d35aa52e47594465c9fdd79083605d9782440023eab48b5a0780a16f45b10fcc20bf410575746f1d4'
token = '268185957:AAHiRcoZG5qgAkEK4vt3i0bIlk8jIg0WGLs'

polo = Poloniex(api_key, api_secret)
bot = telebot.TeleBot(token)
set_id = [4319653, 133974187]


def print_telegram(text):
    print(text)
    for i in set_id:
        bot.send_message(i, text)


def prod(j, array):
    p = 1
    if j == 0:
        return p * (1 - array[0])
    else:
        return prod(j - 1, array) * (1 - array[j])


def suma(i, array):
    if i == 0:
        return array[i]
    else:
        return suma(i - 1, array) + array[i]


def do_sell(currency_pair, rate, amount_sell):
    total_for_sell = rate * amount_sell
    if total_for_sell < 1:
        amount_sell = 1.005 / rate
        sell = polo.sell(currency_pair, rate, amount_sell)
        return sell
    else:
        sell = polo.sell(currency_pair, rate, amount_sell)
        return sell


def numbers_open_orders(currency_pair):
    open_orders = polo.returnOpenOrders(currency_pair)
    list_open_order_number = []
    for i in range(0, len(open_orders)):
        list_open_order_number.append(open_orders[i]['orderNumber'])
    return list_open_order_number


amounts_S = [25, 25, 50, 100, 200]
procent = [0, 0.05, 0.1, 0.2, 0.2]
print(suma(len(amounts_S) - 1, amounts_S))
r_fin = 4
procent_loss = 15
r = 5

print(prod(4, procent) * polo.returnTicker()['USDT_ETH']['last'] * 0.85)
print(prod(4, procent) * 0.95)

t = amounts_S[0] * (r / 100)
print(t)

amounts_S = [25, 25, 50, 100, 200]
procent = [0, 0.05, 0.1, 0.2, 0.2]
r_fin = 4
procent_loss = 15
r = 5

currency_pair = 'USDT_ETH'
coin = currency_pair.split('_')[1]

print_telegram('Starting Bot \nТестова прогонка \nПрацюю із ' + coin)

step = 0

t = 2
sell_order_number = 159354917717
buy_order_number = 159354905729
p0_for_number = 1131.00000001

if (sell_order_number == 0) and (buy_order_number == 0):
    if t == -1:
        pass
    else:
        sys.exit('Uncorrect t, sell_order_number or buy_order_number')

elif (sell_order_number != 0) and (buy_order_number != 0):
    if t != -1:
        list_open_order_number = numbers_open_orders(currency_pair)
        p0 = polo.returnTicker()[currency_pair]['lowestAsk']
        # добпрацювати варіанти згодом
        if (sell_order_number not in list_open_order_number) and (buy_order_number not in list_open_order_number):
            t = -1
            count_coin = polo.returnBalances()[coin]
            sell = polo.sell(currency_pair, p0 * (1 - 0.2), count_coin)
        else:
            pass

    else:
        sys.exit('Uncorrect t, sell_order_number or buy_order_number')

else:
    sys.exit('Uncorrect t, sell_order_number or buy_order_number')

while step <= 10:

    if t == -1:
        p0 = polo.returnTicker()[currency_pair]['lowestAsk']
        print('p0 = ', p0, ' Time:', time.ctime())

        p0_for_number = p0
        number = []
        for j in range(0, len(amounts_S)):
            if j == 0:
                number.append(amounts_S[j] / p0_for_number)
            else:
                number.append(amounts_S[j] / (p0_for_number * prod(j, procent)))

        P_sell = [0] * len(amounts_S)
        for j in range(0, len(amounts_S)):
            P_sell[j] = suma(j, amounts_S) / suma(j, number)
        print(P_sell)

        k0 = number[0]
        print('k0= ', k0)
        p_sell = p0 * (1 + r / 100)
        p_buy = p0 * (1 - procent[1])
        p0_ask = p0 * (1 + 0.03)

        # Если t=-1 то купить buy_0 и виставити 2 ордери - селл та бай 1
        buy = polo.buy(currency_pair, p0_ask, k0)
        buy_order_number = buy['orderNumber']

        text = 'виставили ордер на нульову покупку, p =' + str(p0) + ', k0 = ' + str(round(k0, 5))
        print_telegram(text)

        # не впевнений, що саме тут мають бути оголошенна ця змінна. Подумати!
        sell_loss_order_number = 0
        order_status = 0
        while (order_status < 1):
            time.sleep(2)
            list_open_order_number = numbers_open_orders(currency_pair)
            if (buy_order_number not in list_open_order_number) == True:
                order_status = 1
            else:
                order_status = 0

        print('купили за нульовим ордером\n')
        print('order_status = ', order_status, 'step = ', step)

        count_coin = polo.returnBalances()[coin]
        amount_sell = m.fabs(count_coin - (amounts_S[0] / p_sell))
        sell = do_sell(currency_pair, p_sell, amount_sell)
        sell_order_number = sell['orderNumber']
        print('виставили ордер на sell першого рівня', 'p_sell =', p_sell, 'amount_sell = ', amount_sell)

        k0 = number[1]
        buy = polo.buy(currency_pair, p_buy, k0)
        buy_order_number = buy['orderNumber']
        print('виставили ордер на buy - докуповування першого рівня', 'p_buy =', p_buy, 'k0 = ', k0, '\n\n')

        t = 0

    else:
        number = []
        for j in range(0, len(amounts_S)):
            if j == 0:
                number.append(amounts_S[j] / p0_for_number)
            else:
                number.append(amounts_S[j] / (p0_for_number * prod(j, procent)))
        P_sell = [0] * len(amounts_S)
        for j in range(0, len(amounts_S)):
            P_sell[j] = suma(j, amounts_S) / suma(j, number)
        print(P_sell)

        number = [0] * len(amounts_S)
        for j in range(0, len(amounts_S)):
            if j >= t:
                number[j] = amounts_S[j] / (p0_for_number * prod(j, procent))
                print(number[j])
            else:
                pass
        p_loss = p0_for_number * prod(len(amounts_S) - 1, procent) * (1 - procent_loss / 100)
        print('p_loss = ', p_loss)

    text = 'стан алгоритму:\n' + 't = ' + str(t) + '\nsell_order_number = ' + str(sell_order_number) + \
           '\nbuy_order_number = ' + str(buy_order_number) + '\np0_for_number = ' + str(p0_for_number)
    print_telegram(text)

    index = 0
    while index < 1:
        time.sleep(10)
        list_open_order_number = numbers_open_orders(currency_pair)
        # якщо спрацював оредер на продаж
        if (sell_order_number not in list_open_order_number) == True:
            text = 'продався ордер sell після рівня докуповування t = ' + str(t)
            print_telegram(text)

            ticker = polo.returnTicker()[currency_pair]
            p0 = ticker['highestBid']
            print('p0 = ', p0, ' Time:', time.ctime())

            p0_for_number = p0

            number = []
            for j in range(0, len(amounts_S)):
                if j == 0:
                    number.append(amounts_S[j] / p0_for_number)
                else:
                    number.append(amounts_S[j] / (p0_for_number * prod(j, procent)))
            k0 = number[0]

            P_sell = [0] * len(amounts_S)
            for j in range(0, len(amounts_S)):
                P_sell[j] = suma(j, amounts_S) / suma(j, number)

            time.sleep(1)
            p_sell = p0 * (1 + r / 100)
            count_coin = polo.returnBalances()[coin]
            amount_sell = m.fabs(count_coin - (amounts_S[0] / p_sell))
            sell = do_sell(currency_pair, p_sell, amount_sell)
            sell_order_number = sell['orderNumber']
            print('виставили ордер на sell знову першого рівня', 'p_sell =', p_sell, ' amount_sell = ', amount_sell)

            if (buy_order_number in list_open_order_number) == True:
                print('Скасування попереднього ордеру buy рівня ', t, 'результат - ',
                      polo.cancelOrder(buy_order_number))
            else:
                pass
            # для чого це?
            #             if (sell_loss_order_number in list_open_order_number) == True:
            #                 print('Скасування попереднього ордеру buy рівня ', t, 'результат - ',
            #                       polo.cancelOrder(sell_loss_order_number))
            #             else:
            #                 pass

            p_buy = p0 * (1 - procent[1])
            k0 = number[1]
            buy = polo.buy(currency_pair, p_buy, k0)
            buy_order_number = buy['orderNumber']
            print('виставили ордер на buy - докуповування першого рівня знову', 'p_buy = ', p_buy,
                  'count_coin = ', k0, '\n\n')
            t = 0
            # відправляємо в бот дані про виставлені ордери
            text = 'стан алгоритму:\n' + 't = ' + str(t) + '\nsell_order_number = ' + str(sell_order_number) + \
                   '\nbuy_order_number = ' + str(buy_order_number) + '\np0_for_number = ' + str(p0_for_number)
            print_telegram(text)



        elif (buy_order_number not in list_open_order_number) == True:
            t = t + 1
            ticker = polo.returnTicker()[currency_pair]
            p0 = ticker['highestBid']

            if t < len(amounts_S):

                print('p0 = ', p0, ' Time:', time.ctime())

                text = 'купився ордер buy рівня докуповування t = ' + str(t)
                print_telegram(text)

                if (t + 1) < len(amounts_S):
                    p_buy = p0 * (1 - procent[t + 1])
                    k0 = number[t + 1]
                    buy = polo.buy(currency_pair, p_buy, k0)
                    buy_order_number = buy['orderNumber']
                    print('виставили ордер buy рівня докуповування ', t + 1, 'p_buy = ', p_buy, 'count_coin = ', k0)

                    print('Скасування попереднього ордеру sell рівня ', t, 'результат - ',
                          polo.cancelOrder(sell_order_number))

                    count_coin = polo.returnBalances()[coin]
                    print('coun_coin = ', count_coin)
                    p_sell = P_sell[t] * (1 + r_fin / 100)
                    amount_sell = count_coin - (amounts_S[0] / p_sell)
                    sell = do_sell(currency_pair, p_sell, amount_sell)
                    sell_order_number = sell['orderNumber']
                    print('виставили ордер sell r_fin після рівня докуповування ', t, 'p_sell =', p_sell,
                          'amount_sell = ', amount_sell, '\n\n')

                    text = 'стан алгоритму:\n' + 't = ' + str(t) + '\nsell_order_number = ' + str(sell_order_number) + \
                           '\nbuy_order_number = ' + str(buy_order_number) + '\np0_for_number = ' + str(p0_for_number)
                    print_telegram(text)

                else:
                    print('Скасування попереднього ордеру sell рівня ', t, 'результат - ',
                          polo.cancelOrder(sell_order_number))

                    count_coin = polo.returnBalances()[coin]
                    print('coun_coin = ', count_coin)
                    p_sell = P_sell[t] * (1 + r_fin / 100)
                    amount_sell = count_coin - (amounts_S[0] / p_sell)
                    sell = do_sell(currency_pair, p_sell, amount_sell)
                    sell_order_number = sell['orderNumber']
                    print('виставили ордер sell r_fin після рівня докуповування ', t, 'p_sell =', p_sell,
                          'amount_sell = ', amount_sell, '\n\n')

                    p_loss = p0 * (1 - procent_loss / 100)
                    print('Очікуємо на stoploss, p_loss = ', p_loss, 'p0 = ', p0)

                    text = 'стан алгоритму:\n' + 't = ' + str(t) + '\nsell_order_number = ' + str(sell_order_number) + \
                           '\nwaiting stop_loss ' + '\nOld_buy_order_number = ' + str(buy_order_number) + \
                           '\np0_for_number = ' + str(p0_for_number)
                    print_telegram(text)
            #         чи правильно тут йде оголошення p_loss

            else:
                if p0 <= p_loss:
                    if sell_loss_order_number == 0:
                        # момент stoploss -- скасування поперднього ордеру для sell і продати усе за ціною p_loss
                        p_sell_loss = p0 * (1 - 0.2)
                        print('відміняємо ордер sell для виконання stoploss ', polo.cancelOrder(sell_order_number))
                        count_coin = polo.returnBalances()[coin]
                        sell_loss = polo.sell(currency_pair, p_sell_loss, count_coin)
                        sell_loss_order_number = sell_loss['orderNumber']
                        print('виставили ордер sell stoploss', ' p_sell_loss = ', p0, 'K = ', count_coin)

                        text = 'стан алгоритму:\n' + 't = ' + str(t) + '\nfinal sell_loss_order_number ' + \
                               str(sell_loss_order_number) + '\nOld_sell_order_number = ' + str(sell_order_number) + \
                               '\nOld_buy_order_number = ' + str(buy_order_number) + \
                               '\np0_for_number = ' + str(p0_for_number)
                        print_telegram(text)

                        for i in range(0, len(open_orders)):
                            list_open_order_number.append(open_orders[i]['orderNumber'])

                        if (sell_loss_order_number not in list_open_order_number) == True:
                            text = 'продали за ордером sell stoploss - починаємо з початку, p = ' + str(p0) + \
                                   ', k = ' + str(round(count_coin, 5))
                            print_telegram(text)
                            print('\n\n')

                            step = step + 1
                            index = 1
                            t = -1

                        else:
                            pass

                    else:
                        for i in range(0, len(open_orders)):
                            list_open_order_number.append(open_orders[i]['orderNumber'])
                        if (sell_loss_order_number not in list_open_order_number) == True:

                            text = 'продали за ордером sell stoploss - починаємо з початку, p = ' + str(p0)
                            print('\n\n')

                            step = step + 1
                            index = index + 1
                            t = -1
                        else:
                            pass

                else:
                    pass
