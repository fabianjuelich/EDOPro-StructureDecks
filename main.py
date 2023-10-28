import customtkinter as ctk
import tkinter as tk
from tkinter.messagebox import askretrycancel
from tktooltip import ToolTip
from PIL import Image
import requests
from io import BytesIO
import os
import logging
from configparser import ConfigParser
import platform
from threading import Thread

PLATFORM = platform.system()

logging.basicConfig(level = logging.INFO, filename='.EDOPro_SD.log', filemode='w', format='%(levelname)s: %(asctime)s: %(message)s')

def abs_path(path): return os.path.join(os.path.dirname(__file__), path)

PROJECT_IGNIS_DEFAULT = os.path.join(os.path.abspath(os.sep), 'ProjectIgnis')
config = ConfigParser()
if not os.path.exists(('.EDOPro_SD.ini')):
    config.add_section('ProjectIgnis')
    config.set('ProjectIgnis', 'path', PROJECT_IGNIS_DEFAULT)
    with open(('.EDOPro_SD.ini'), 'w') as ini:
        config.write(ini)
    logging.info('Default config-file created')
config.read(('.EDOPro_SD.ini'))
logging.info(dict(map(lambda s: (s, dict(config.items(s))), config.keys())))
PROJECT_IGNIS = config.get('ProjectIgnis', 'path')

SET_LIST = 'https://db.ygoprodeck.com/api/v7/cardsets.php'
CARD_LIST = 'https://yugiohprices.com/api/set_data/'
CARD_INFO = 'https://db.ygoprodeck.com/api/v7/cardinfo.php?name='

class App(ctk.CTk):
    
    def __init__(self):
        super().__init__()

        self.title('EDOPro SD')
        icon = tk.PhotoImage(file=abs_path('assets/icons8-card-game-66.png'))
        self.iconphoto(True, icon)

        self.combobox = ctk.CTkComboBox(self, command=self.select)
        self.combobox.set('Search')
        self.logo = ctk.CTkImage(Image.open(abs_path('assets/EDOPro_logo.png')), size=(100, 164))
        self.button = ctk.CTkButton(self, text='', fg_color='transparent', image=self.logo, state='disabled', command=self.save)
        self.label = ctk.CTkLabel(self, text='Connecting...')

        self.combobox.pack()
        self.button.pack()
        self.label.pack()

        self.combobox.bind('<KeyRelease>', self.search)
        self.combobox.bind('<Return>', self.save)
        self.combobox.bind('<FocusIn>', self.delete)

        self.prompt = True
        self.unlock = False
        self.cnt = 1
        self.selected = None

        ToolTip(self.button, msg=lambda: self.selected['set_name'] if self.selected else '', bg='#1c1c1c', fg='#ffffff')

        self.after(0, self.connect)

    def connect(self):
        while True: 
            try:
                self.set_list = dict(filter(lambda sd: bool(sd), list(map(lambda obj: (obj['set_name'], obj) if 'structure deck' in obj['set_name'].lower() else {}, requests.get(SET_LIST).json()))))
                logging.info('Connected')
                break
            except Exception as e:
                logging.warning(e)
                if not askretrycancel('Connection error', 'Check your network connection, proxy and firewall.'):
                    self.destroy()
                    break

        self.combobox.configure(values=list(map(lambda sd: sd[0], self.set_list.items())))
        self.label.configure(text='Choose deck')

    def enableInput(self, enable):
        self.combobox.configure(state=('normal' if enable else 'disabled'))
        self.button.configure(state=('normal' if enable else 'disabled'))

    def default_combobox(self):
        self.combobox.configure(values=list(map(lambda sd: sd[0], self.set_list.items())))

    def show_image(self, sd):
        if sd:
            self.selected = sd
            img = ctk.CTkImage(Image.open(BytesIO(requests.get(sd['set_image']).content)), size=(100, 164))
            self.button.configure(image=img, state='normal')
            if f'{sd["set_name"].replace(":", "")}.ydk' in os.listdir(os.path.join(PROJECT_IGNIS, 'deck')):
                self.label.configure(text='Already added')
            else:
                self.label.configure(text='Click deck to add')
        else:
            self.button.configure(image=self.logo, state='disabled')
            self.selected = None
            self.label.configure(text='Choose deck')

    def search(self, event):
        self.selected
        results = []
        for set in self.set_list:
            if self.combobox.get().strip().lower() in set.lower():
                results.append(self.set_list[set])
        self.combobox.configure(values=list(map(lambda r: r['set_name'], results)))
        if len(results) == 1:
            if results[0] != self.selected:
                self.show_image(results[0])
        else:
            if self.selected:
                self.show_image(None)

    def select(self, event):
        self.default_combobox()
        if self.set_list[self.combobox.get()] != self.selected:
            self.show_image(self.set_list[self.combobox.get()])
        self.unlock = True
        self.focus()

    def save_background(self):
        self.combobox.set(self.selected['set_name'])
        self.enableInput(False)
        self.label.configure(text='Please wait...')
        self.update()
        passwords = {'main': [], 'extra': []}
        try:
            for card in ((requests.get(CARD_LIST+self.selected['set_name'])).json()['data']['cards']):
                card_info = (requests.get(CARD_INFO+(card['name']).replace('&', '%26')).json())
                if 'data' in card_info:
                    passwords['extra' if card_info['data'][0]['frameType'] in ['fusion', 'synchro', 'xyz', 'link'] else 'main'].append(str(card_info['data'][0]['id']))
                else:
                    logging.warning(f'"{card["name"]}" not found')
            with open(os.path.join(PROJECT_IGNIS, 'deck', f'{self.selected["set_name"].replace(":", "")}.ydk'), 'w') as deck:
                deck.write('#created by Player\n'+'#main\n'+'\n'.join(passwords['main'])+'\n#extra\n'+'\n'.join(passwords['extra'])+'\n!side')
            self.label.configure(text='Deck added')
        except Exception as e:
            logging.error(e)
            self.label.configure(text='Something went wrong')
        self.prompt = True
        self.focus()
        self.enableInput(True)
        self.default_combobox()

    def save(self, event=None):
        Thread(target=self.save_background).start()

    def delete(self, event):
        if self.unlock:
            self.cnt += 1
        if self.prompt or (self.unlock and self.cnt==(2 if PLATFORM == 'Linux' else 1)):
            self.combobox.set('')
            self. show_image(None)
            self.prompt = False
            self.unlock = False
            self.cnt = 0

app = App()
app.mainloop()