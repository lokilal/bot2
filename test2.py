import telebot
import time
import datetime
from mysql.connector import Error
from multiprocessing import *
import schedule
import mysql.connector
from telebot import types
import pandas as pd
import plotly.graph_objs as go

"""
Работающий бот
"""

bot = telebot.TeleBot('1656502971:AAFlJSfiLpEH8t0Eg3GBkQdcgMNlGNtaf5o')
bd = mysql.connector.connect(
    host="localhost",
    user="root",
    password="kit456",
    port="3306",
    database="bot"
)
cursor = bd.cursor()

cursor.execute("SELECT time, user_id FROM users WHERE time != 'NULL'")
row = cursor.fetchall()


def start_process():  # Запуск Process
    p1 = Process(target=P_schedule.start_schedule, args=()).start()


class P_schedule():  # Class для работы с schedule

    def start_schedule():  # Запуск schedule
        ######Параметры для schedule######
        P_schedule.send_message1()
        schedule.every().day.at("00:00").do(P_schedule.create_new_column)
        schedule.every().day.at("00:03").do(P_schedule.add_value)
        for x, y in row:  # Пробегаемся по БД, и запускаем функцию отправки сообщения
            schedule.every().day.at(x).do(P_schedule.send_message1)

        ##################################

        while True:  # Запуск цикла
            schedule.run_pending()
            time.sleep(1)

    ####Функции для выполнения заданий по времени
    def send_message1():
        for x, y in row:  # Проверяет текущее время с тем, что указано в БД
            now = datetime.datetime.now()  # Для работы со временем
            if now.strftime("%H:%M") == x:
                try:
                    bot.send_message(y, 'Эй, пора начинать готовиться к ЕГЭ! ')
                    print("Сработал будильник у " + str(y))
                except Exception as e:
                    print(str(y) + " Заблокировал бота")

    ################ В 00:00 создает новый столбец
    def create_new_column():
        now = datetime.datetime.now()
        try:
            sql = "ALTER TABLE `users` ADD `{:s}` VARCHAR (255)".format(str(now.strftime("%d.%m.%Y")))
            cursor.execute(sql)
        except Exception as e:
            print("Таблица уже создана")


    def add_value(): # Добавляет дату для статистики
        now = datetime.datetime.now()
        sql = "UPDATE `users` SET `{:s}` = '{:s}' WHERE  `id` = '1'".format(str(now.strftime("%d.%m.%Y")),
                                                                            str(now.strftime("%d.%m.%Y")))
        cursor.execute(sql)
        bd.commit()


###Настройки команд telebot######### Общение между ботом и пользователем.


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            if call.data == "time":
                bot.send_message(call.message.chat.id, 'Напишите во сколько отправлять вам уведомления в формате xx:xx.'
                                                       'Например: 21:20 или 09:05')
            if call.data == "new_res":
                bot.send_message(call.message.chat.id, 'Напишите ваш результат.')
            if call.data == "stat":
                try:
                    statistic(call.message.chat.id)
                except Exception as e :
                    bot.send_message(call.message.chat.id, "Вы не добавили результаты")
    except Exception as e:
        print("No")


@bot.message_handler(commands=['help'])
def start_message(message):
    bot.send_message(message.chat.id, 'Этот бот поможет при подготовке к ЕГЭ')


@bot.message_handler(commands=['start'])
def start_message(message):
    otvet = types.InlineKeyboardMarkup(row_width=2)
    button1 = types.InlineKeyboardButton(" Изменить время", callback_data='time')
    button2 = types.InlineKeyboardButton(" Добавить результат", callback_data='new_res')
    button3 = types.InlineKeyboardButton(" Показать статистику", callback_data='stat')
    otvet.add(button1, button2, button3)
    bot.send_message(message.chat.id,
                     text='Привет, ты написал боту, который помогает отслеживать результаты подготовки к ЕГЭ. '
                          'Для того, чтобы узнать на что способен этот бот - напиши /help ', reply_markup=otvet)
    try:
        sql = "INSERT INTO Users (time,  user_id) VALUES (%s,  %s)"
        val = ('NULL', message.from_user.id)
        cursor.execute(sql, val)
        bd.commit()
        print("Опа, новенький! " + str(message.from_user.id) + " ,Вот он")
    except:
        print("Сообщение от старичков, а именно от " + str(message.from_user.id))


@bot.message_handler(commands=['stat'])
def start_message(message):
    statistic(message.chat.id)



@bot.message_handler(content_types=['text'])
def message(message):
    try:
        # Проверка сообщения на время.
        if len(message.text) == 5 and 0 <= int(message.text[:2]) < 24 and 0 <= int(message.text[3:]) < 60 and \
                message.text[2] == ':':
            try:
                print("Кто-то решил установить будильник/ Изменить время будильника " + str(message.from_user.id))
                sql = "UPDATE users SET time = (%s) WHERE  user_id = (%s)"
                val = (message.text, message.from_user.id)
                cursor.execute(sql, val)
                bd.commit()
                bot.send_message(message.chat.id, "Ваше время изменено " + message.text)
            except Exception as e:
                print("Проблемы с таблицей")
        if len(message.text) <= 3 and 0 <= int(message.text) <= 100:
            now = datetime.datetime.now()
            try:  # Создаем столбец, название - сегодняшяя дата.
                sql = "UPDATE `users` SET `{:s}` = (%s) WHERE  user_id = (%s)".format(str(now.strftime("%d.%m.%Y")))
                val = (message.text, message.from_user.id)
                cursor.execute(sql, val)
                bd.commit()
                bot.send_message(message.chat.id, "Успешно добавлено ")
            except Exception as e:
                print("Проблемы с добавлением нового результат в БД")



    except ValueError:
        bot.send_message(message.chat.id, 'Время пишется цифрами')



##################### Закончился блок ,связанный с общением с ботом.


# Блок, связанный с отправкой стистики.
def query_to_bigquery(query): # при цикле нужно сделать try, если не работает, то отправлять письмо.
    cursor.execute(query)
    result = cursor.fetchall()
    temp = [tuple(int(result[0][i]) for i in range(3, len(*result)) if result[0][i] != None)]
    id_for_delete = [i-3 for i in range(3, len(*result)) if result[0][i] != None] # Хранятся номера, которые не нужно удалить
    id_for_delete.sort()
    cursor.execute("SELECT * FROM `users` WHERE id = '1';")
    tmp = cursor.fetchall()
    temp2 = [tmp[0][i] for i in range(3, len(*result))] # Массив, в котором хранятся даты
    temp3 = [temp2[i] for i in id_for_delete]
    data = [tuple(temp3), temp[0]]
    dataframe = pd.DataFrame(data, index=['time', 'res']).T
    if len(dataframe) == 0:
        return None
    else: return dataframe


def get_and_save_image(id):  # Рисует график
    query = "SELECT * FROM `users` WHERE user_id = '{:s}'".format(str(id))
    dataframe = query_to_bigquery(query)  # Получение DataFrame
    x = dataframe['time'].tolist()
    y = dataframe['res'].tolist()
    layout = dict(plot_bgcolor='white',
                  margin=dict(t=35, l=20, r=20, b=10),
                  xaxis=dict(title='Дата',
                             range=[-1, 5.5],
                             linecolor='#d9d9d9',
                             showgrid=False,
                             mirror=True),
                  yaxis=dict(title='Результат',
                             range=[0, 100],
                             linecolor='#d9d9d9',
                             showgrid=False,
                             mirror=True))

    data = go.Scatter(x=x,
                      y=y,
                      text=y,
                      textposition='top right',
                      textfont=dict(color='#E58606'),
                      mode='lines+markers+text',
                      marker=dict(color='#5D69B1', size=9),
                      line=dict(color='#52BCA3', width=1, dash='dash'),
                      name='citations')

    fig = go.Figure(data=data, layout=layout)
    fig.update_layout(
        title_text="Статистика"
    )
    fig.write_image("viz.png")


def send_image(id):
    get_and_save_image(id)
    bot.send_photo(chat_id=id, photo=open('viz.png', 'rb'))
    print(str(id) + " Понадобилась статистика")


def statistic(id):
    send_image(id)


# Закончился блок со статистикой


if __name__ == '__main__':
    start_process()
    try:
        bot.polling(none_stop=True)
    except:
        pass
