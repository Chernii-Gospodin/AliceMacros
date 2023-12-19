import customtkinter as ctk
import requests
import json
import os
import pystray
import PIL
from time import sleep
import threading
import pyperclip


class FirstWindow(ctk.CTk):
    USER_ID = None

    def __init__(self):
        super().__init__()

        self.title('MACROS')
        self.geometry('400x400')
        self.resizable(False, False)
        self.attributes('-alpha', 0.95)

        self.InsertIdLabel = ctk.CTkLabel(self, text='Скопируйте USER_ID и нажмите на кнопку')
        self.InsertIdLabel.pack(anchor='w')

        self.WarningLabel = ctk.CTkLabel(self, text='После ввода USER_ID команды будут доступны в трее')
        self.WarningLabel.pack(anchor='w')

        self.NotUserID = ctk.CTkLabel(self, text='Неправильный USER_ID', text_color='red')

        self.button = ctk.CTkButton(self, text='Я скопировал USER_ID', command=self.insert)
        self.button.pack()

    def insert(self):
        memory = pyperclip.paste()
        if len(memory) == 64:
            FirstWindow.USER_ID = pyperclip.paste()
            self.destroy()
        else:
            self.NotUserID.pack()


class Stray:
    def __init__(self):
        self.image = PIL.Image.open(r'logo.png')
        self.program_condition = 'ЗАПУСТИТЬ программу'
        self.thread_event = threading.Event()
        self.thread = threading.Thread(target=main_program, args=(self.thread_event,)).start()
        self.icon = pystray.Icon('Macros', self.image,
                                 menu=pystray.Menu(
                                     pystray.MenuItem('ЗАКРЫТЬ программу', self.close_icon),
                                     pystray.MenuItem(
                                         f'USER_ID: {FirstWindow.USER_ID[:7]}...{FirstWindow.USER_ID[-7:]}', None)
                                 ))

    def close_icon(self):
        self.thread_event.set()
        self.icon.stop()


def main_program(thr_event: threading.Event()):
    while True:
        response = requests.post(url='https://functions.yandexcloud.net/d4e2lg5232b57723d4ek', data=FirstWindow.USER_ID,
                                 headers={'Content-Type': 'application/json'}).text
        if response != 'None':
            response = json.loads(response)
            temp_memory = []
            for elem in response:
                elem = elem.strip("\'\r\"")

                try:
                    os.startfile(elem)
                except FileNotFoundError:
                    temp_memory.append(elem)

            if temp_memory:
                filenotfound = ''
                for elem in temp_memory:
                    filenotfound += elem +'\n'

                def window():
                    temp_window = ctk.CTk()
                    temp_window.title('Не удалось открыть файл/ссылку')

                    temp_label = ctk.CTkLabel(temp_window, text=f'Не удалось найти следующие файлы/ссылки:\n{filenotfound}')
                    temp_label.pack()

                    temp_button = ctk.CTkButton(temp_window, text='Выйти', command=temp_window.destroy)
                    temp_button.pack()

                    temp_window.mainloop()

                threading.Thread(target=window, args=()).start()

        if thr_event.is_set():
            break
        sleep(0.7)


if __name__ == '__main__':
    display = FirstWindow()
    display.mainloop()

    if FirstWindow.USER_ID is not None:
        stray = Stray()
        stray.icon.run()
