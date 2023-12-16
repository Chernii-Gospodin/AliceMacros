import customtkinter as ctk
import requests
import json
import os
import pystray
import PIL
from time import sleep
import threading
import pyperclip


class Display(ctk.CTk):
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

        self.button = ctk.CTkButton(self, text='Я скопировал USER_ID', command=self.insert)
        self.button.pack()

    def insert(self):
        Display.USER_ID = pyperclip.paste()
        self.destroy()


class Stray:
    def __init__(self):
        self.__image = PIL.Image.open(r'logo.png')
        self.program_condition = 'ЗАПУСТИТЬ программу'
        self.thread_event = threading.Event()
        self.thread = threading.Thread(target=main_program, args=(self.thread_event,))
        self.icon = pystray.Icon('Macros', self.__image,
                                 menu=pystray.Menu(
                                     pystray.MenuItem('ЗАКРЫТЬ программу', self.click),
                                     pystray.MenuItem('ЗАПУСТИТЬ программу', self.click),
                                     pystray.MenuItem(f'USER_ID: {Display.USER_ID[:14]}...', None)
                                 ))

    def click(self, icon, item):
        if item.text == 'ЗАКРЫТЬ программу':
            self.thread_event.set()
            self.icon.stop()
        elif item.text == 'ЗАПУСТИТЬ программу':
            self.thread.start()


def main_program(thr_event: threading.Event()):
    while True:
        response = requests.post(url='https://functions.yandexcloud.net/d4e2lg5232b57723d4ek', data=Display.USER_ID,
                                 headers={'Content-Type': 'application/json'}).text
        if response != 'None':
            response = json.loads(response)
            for elem in response:
                elem = elem.strip("\'\r\"")
                os.startfile(elem)
        sleep(0.7)
        if thr_event.is_set():
            break


if __name__ == '__main__':
    display = Display()
    display.mainloop()

    if Display.USER_ID is not None:
        stray = Stray()
        stray.icon.run()
