import customtkinter as ctk
import tkinter as tk
from PIL import Image
import requests
from io import BytesIO
import os
import logging
from configparser import ConfigParser
import platform
from threading import Thread

PLATFORM = platform.system()

logging.basicConfig(level = logging.INFO, filename='.EDOpro_SD.log', filemode='w', format='%(levelname)s: %(asctime)s: %(message)s')

def abs_path(path): return os.path.join(os.path.dirname(__file__), path)

PROJECT_IGNIS_DEFAULT = os.path.join(os.path.abspath(os.sep), 'ProjectIgnis')
config = ConfigParser()
if not os.path.exists(('.EDOpro_SD.ini')):
    config.add_section('ProjectIgnis')
    config.set('ProjectIgnis', 'path', PROJECT_IGNIS_DEFAULT)
    with open(('.EDOpro_SD.ini'), 'w') as ini:
        config.write(ini)
    logging.info('Default config-file created')
config.read(('.EDOpro_SD.ini'))
logging.info(dict(map(lambda s: (s, dict(config.items(s))), config.keys())))
PROJECT_IGNIS = config.get('ProjectIgnis', 'path')

SET_LIST = 'https://db.ygoprodeck.com/api/v7/cardsets.php'
CARD_LIST = 'https://yugiohprices.com/api/set_data/'
CARD_INFO = 'https://db.ygoprodeck.com/api/v7/cardinfo.php?name='

set_list = dict(filter(lambda sd: bool(sd), list(map(lambda obj: (obj['set_name'], obj) if 'structure deck' in obj['set_name'].lower() else {}, requests.get(SET_LIST).json()))))
prompt = True
unlock = False
cnt = 1
selected = None

def show_image(sd):
    global selected
    if sd:
        selected = sd
        img = ctk.CTkImage(Image.open(BytesIO(requests.get(sd['set_image']).content)), size=(100, 164))
        image_holder.configure(image=img, state='normal')
        if f'{sd["set_name"].replace(":", "")}.ydk' in os.listdir(os.path.join(PROJECT_IGNIS, 'deck')):
            label.configure(text='Already added')
        else:
            label.configure(text='Click deck to add')
    else:
        image_holder.configure(image=logo, state='disabled')
        selected = None
        label.configure(text='Choose deck')

def search(event):
    global selected
    results = []
    for set in set_list:
        if combobox.get().strip().lower() in set.lower():
            results.append(set_list[set])
    combobox.configure(values=list(map(lambda r: r['set_name'], results)))
    if len(results) == 1:
        show_image(results[0])
    else:
        show_image(None)

def unfold(event):
    global unlock
    combobox.configure(values=list(map(lambda sd: sd[0], set_list.items())))
    show_image(set_list[combobox.get()])
    unlock = True
    app.focus()

def save_background():
    label.configure(text='Please wait...')
    app.update()
    passwords = {'main': [], 'extra': []}
    try:
        for card in ((requests.get(CARD_LIST+selected['set_name'])).json()['data']['cards']):
            card_info = (requests.get(CARD_INFO+(card['name']).replace('&', '%26')).json())
            if 'data' in card_info:
                passwords['extra' if card_info['data'][0]['frameType'] in ['fusion', 'synchro', 'xyz', 'link'] else 'main'].append(str(card_info['data'][0]['id']))
            else:
                logging.warning(f'"{card["name"]}" not found')
        with open(os.path.join(PROJECT_IGNIS, 'deck', f'{selected["set_name"].replace(":", "")}.ydk'), 'w') as deck:
            deck.write('#created by Player\n'+'#main\n'+'\n'.join(passwords['main'])+'\n#extra\n'+'\n'.join(passwords['extra'])+'\n!side')
        label.configure(text='Deck added')
    except Exception as e:
        logging.error(e)
        label.configure(text='Something went wrong')

def save():
    Thread(target=save_background).start()

def delete(event):
    global prompt
    global unlock
    global cnt
    if unlock:
        cnt += 1
    if prompt or (unlock and cnt==(2 if PLATFORM == 'Linux' else 1)):
        combobox.set('')
        show_image(None)
        prompt = False
        unlock = False
        cnt = 0

app = ctk.CTk()
app.title('EDOpro SD')
icon = tk.PhotoImage(file=abs_path('assets/icons8-card-game-66.png'))
app.iconphoto(True, icon)

combobox = ctk.CTkComboBox(app, values=list(map(lambda sd: sd[0], set_list.items())), command=unfold)
combobox.set('Search')

logo = ctk.CTkImage(Image.open(abs_path('assets/EDOpro_logo.png')), size=(100, 164))
image_holder = ctk.CTkButton(app, text='', fg_color='transparent', image=logo, state='disabled', command=save)
label = ctk.CTkLabel(app, text='Choose deck')

combobox.pack()
image_holder.pack()
label.pack()

combobox.bind('<KeyRelease>', search)
combobox.bind('<FocusIn>', delete)

app.mainloop()