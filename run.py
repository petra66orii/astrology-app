# Import neccesary packages for our app
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from kerykeion import AstrologicalSubject, Report, KerykeionChartSVG
import questionary

# This section of code is borrowed from the "Love Sandwiches" project
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
    ]

CREDS = Credentials.from_service_account_file('creds.json')
SCOPED_CREDS = CREDS.with_scopes(SCOPE)
GSPREAD_CLIENT = gspread.authorize(SCOPED_CREDS)
SHEET = GSPREAD_CLIENT.open('astrology_app')

# Define the sheet variables
horoscope_sheet = SHEET.worksheet('horoscope')
birth_chart_sheet = SHEET.worksheet('birth_chart')

def start_app():
    """
    Starts the app by asking the user to pick an option: 
    Horoscope or Birth Chart
    """
    print("Welcome to AstrologyApp!")
    options = ['Horoscope', 'Birth Chart']

    select_option = (questionary.select('Select an option:', choices=options).ask())

    if select_option == 'Horoscope':
        return 'Horoscope'
    elif select_option == 'Birth Chart':
        return 'Birth Chart'


start_app()