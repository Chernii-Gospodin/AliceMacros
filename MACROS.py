import tkinter as tk
from requests import post as POST
from json import loads as LOADS
from os import startfile as STFILE, path as PATH
from time import sleep


USER_ID = None
if PATH.exists('user_id.txt'):
    with open('user_id.txt', 'r') as f:
        USER_ID = f.readline()
else:
    USER_ID = input('Введите ваш ID: ')
    with open('user_id.txt', 'w') as f:
        f.write(USER_ID)

URL = 'https://functions.yandexcloud.net/d4e2lg5232b57723d4ek'
header_setting = {'Content-Type': 'application/json'}
print('Программа выполняется')
while True:
    response = POST(url=URL, data=USER_ID, headers=header_setting).text

    if response != 'None':
        response = LOADS(response)
        for elem in response:
            elem = elem.strip("\'\r\"")
            STFILE(elem)
    sleep(0.2)
