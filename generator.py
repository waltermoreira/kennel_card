import os
import httplib2
import datetime
import argparse
import io
import sys
import datetime

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 

import pygsheets
import fpdf
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.http import MediaIoBaseDownload


def get_env_var(name):
    try:
        return os.environ[name]
    except KeyError:
        print('Environment variable {0} is needed'.format(name.upper()))
        

SHEET = get_env_var('SHEET')
FOLDER = get_env_var('FOLDER')


#SHEET = '1bfedgkbyRgiZxEqmb9QXQHdu3ZV3BNgPVb327ku4e2Y'
#FOLDER = '0B3qV0KkMXsKxbHRCVWhVT1NXcGc'

things = [
    ('Car rides', 'go-for-car-rides.jpg'),
    ('Cats', 'hang-out-with-cats.jpg'),
    ('Couch potato', 'be-a-couch-potato.jpg'),
    ('Do tricks', 'do-tricks.jpg'),
    ('Dogs', 'play-with-some-dogs.jpg'),
    ('Entertain myself', 'entertain-myself.jpg'),
    ('Fetch', 'play-fetch.jpg'),
    ('Home alone', 'stay-home-alone.jpg'),
    ('Keep you safe', 'keep-you-safe.jpg'),
    ('Kids', 'hang-out-with-kids.jpg'),
    ('Out on the town', 'go-out-on-the-town.jpg'),
    ('Run', 'go-for-runs.jpg'),
    ('Swim', 'go-swimming.jpg'),
    ('Wear outfits', 'wear-outfits.jpg')
]

ALL_THINGS = dict(things)


def concatenate(filenames, into='out.pdf'):
    pdf = fpdf.FPDF(unit='pt', format=(2550, 3300))
    for image in filenames:
        pdf.add_page()
        pdf.image(image, 0, 0)
    pdf.output(into, "F")


def break_text(text, font, maxsize=2300):
    partial = []
    for c in text.split():
        s = font.getsize(' '.join(partial))[0]
        if s > maxsize:
            yield ' '.join(partial)
            partial = []
        partial.append(c)
    yield ' '.join(partial)


DOG_NAME = 'Buddy Franklin'
SEX = 'Male'
BIRTHDATE = '9/15/2011'
LOOKS_LIKE = 'Pitbull / Pig / Raccoon mix'
THINGS = ['Swim', 'Wear outfits', 'Kids']
UNIQUE = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit, 
sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi 
ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit
in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur 
sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit 
anim id est laborum.'''
DOG_PIC = 'test2.jpg'


def generate(dog_name, sex, birthdate, looks_like, things, unique, dog_pic):
    col1 = 60
    col2 = 1800

    img = Image.open("New Kennel Card Files/kennel-card-blank.jpg")
    draw = ImageDraw.Draw(img)

    font1 = ImageFont.truetype("fonts/Lato-Regular.ttf", 280)
    font2 = ImageFont.truetype("fonts/Lato-Regular.ttf", 100)
    font3 = ImageFont.truetype("fonts/Lato-Regular.ttf", 80)
    font4 = ImageFont.truetype("fonts/Lato-Light.ttf", 60)

    draw.text((col1, 230), dog_name, (0,0,0), font=font1)
    draw.text((col2, 750), sex, (0,0,0), font=font2)
    draw.text((col2, 1050), birthdate, (0,0,0), font=font2)
    looks = [x.strip() for x in looks_like.split('/')]

    for i, look in enumerate(looks):
        draw.text((col2, 1370+i*100), look, (0,0,0), font=font3)

    for i, thing in enumerate(things):
        full_path = os.path.join('New Kennel Card Files/icons', ALL_THINGS[thing])
        icon = Image.open(full_path)
        img.paste(icon, (78+i*290, 2200))

    for i, line in enumerate(break_text(unique, font4, 2200)):
        draw.text((82, 2780+i*70), line, (0,0,0), font=font4)

    pic = Image.open(dog_pic)
    p = pic.resize((1656, int(1656*pic.height/pic.width)))
    h = (p.height-1250)/2
    q = p.crop((0, h, 1656, 1250+h))
    img.paste(q, (79, 677))

    return img


def get_sheet(sheet_id):
    c = pygsheets.authorize(service_file='secret.json')
    sheet = c.open_by_key(sheet_id)
    return sheet.worksheet_by_title('Sheet1')

def get_drive():
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'secret.json', scopes=['https://www.googleapis.com/auth/drive'])
    http = creds.authorize(httplib2.Http())
    return discovery.build('drive', 'v3', http=http)

def select_things(vector):
    for ((k, _), x) in zip(things, vector):
        if x:
            yield k
            

class PictureNotFound(Exception):
    pass


class Cards(object):
    
    def __init__(self, sheet=SHEET, folder=FOLDER):
        self.worksheet = get_sheet(sheet)
        self.folder = folder
        self.drive = get_drive()
        self.rows = self.worksheet.all_values()

    def get_row(self, idx):
        return self.rows[idx-1]
    
    def download(self, file_id, target):
        request = self.drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        with open(target, 'w+b') as out:
            out.write(fh.getvalue())

    def get_picture(self, dog_name):
        q = "'{folder}' in parents and not trashed".format(folder=self.folder)
        files = self.drive.files().list(
            q=q, fields='files(description,id,name)').execute()
        for file in files['files']:
            name, _ = os.path.splitext(file['name'])
            if name == dog_name:
                target = os.path.join('pictures', file['name'])
                self.download(file['id'], target)
                return target
        raise PictureNotFound(dog_name)

    def generate_row(self, row):
        dog_name, sex, birthdate, looks_like, unique, *vector = self.get_row(row)
        things = select_things(vector)
        dog_pic = self.get_picture(dog_name)
        return generate(dog_name, sex, birthdate,
                        looks_like, things, unique, dog_pic)

    def generate_file_for_row(self, row):
        img = self.generate_row(row)
        filename = '/tmp/{}.jpg'.format(self.get_row(row)[0])
        img.save(filename)
        return filename

    def generate_file_for_rows(self, rows):
        filenames = [self.generate_file_for_row(row) for row in rows]
        concatenate(filenames)
            