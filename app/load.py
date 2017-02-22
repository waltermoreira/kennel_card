import csv
import itertools

import requests
from bs4 import BeautifulSoup

import generator


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def get_indices():
    r = requests.get('http://www.dogdiaries.dreamhosters.com/')
    soup = BeautifulSoup(r.text, 'html.parser')
    all_td = soup.find_all('td', class_='wideview')
    return [y[0] for y in grouper([x.text for x in all_td], 8)]

def data_for_index(idx):
    url = ('https://www.austinpetsalive.org/adopt/available-dog-details/?ID={}'
           .format(idx))
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    loc = next(soup.select_one('#detail-table').select('tr td')[-1].strings)
    if loc != 'TLAC':
        return None
    
    s = soup.select_one('#detail-table tr td:nth-of-type(2)').text
    u = soup.select_one('#detail-table tr td:nth-of-type(3)')
    l = ' '.join(u.strings)
    return {
        'name': soup.find('h2').text,
        'sex': 'Male' if s == 'M' else 'Female',
        'looks': l.replace(',', '/'),
        'birthdate': soup.select_one('#detail-table tr td:nth-of-type(5)').text,
    }

        
def fill():
    c = generator.Cards()
    values = []
    for idx in get_indices():
        print(f'processing {idx}')
        d = data_for_index(idx)
        if d is None:
            print('  not at TLAC')
            continue

        print(f'  doggie {d["name"]}')
        values.append([d['name'], d['sex'], d['birthdate'], d['looks']])
    c.worksheet.update_cells('A4', values)
    
            
def download_pics():
    for idx in get_indices():
        print(f'downloading {idx}')
        url = ('https://www.austinpetsalive.org/adopt/available-dog-details/?ID={}'
               .format(idx))
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')

        loc = next(soup.select_one('#detail-table').select('tr td')[-1].strings)
        if loc != 'TLAC':
            print('  not at TLAC')
            continue
        
        s = soup.select_one('#detail-table tr td:nth-of-type(2)').text
        name = soup.find('h2').text

        img = soup.select_one('#main_image').attrs['src'].split('?')[0]
        ext = img.split('.')[-1]
        print(f' downloading {name}')
        r = requests.get(img)
        with open(f'pics/{name}.{ext}', 'wb') as f:
            f.write(r.content)
