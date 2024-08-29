# Import neccesary packages for our app
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime as dt
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
        horoscope()
    elif select_option == 'Birth Chart':
        return 'Birth Chart'

def validate_name(name):
    """
    Validates name so it can only contain alphabetic characters 
    and can't be longer than 50 characters.
    """
    if not name.isalpha() or len(name) >= 50:
        raise TypeError('Invalid name. Name can only contain alphabetic characters and have max 50 or less characters.')
    return

def validate_date(date):
    """
    Validates date of birth so it is in DD/MM/YYYY format
    """
    try:
        valid_date = dt.strptime(date, '%d/%m/%Y')
    except ValueError:
        raise ValueError('Invalid date. Please enter the date in DD/MM/YYYY format.')
    return

def horoscope():
    """
    Takes input from the user, validates it and returns the user's 
    zodiac sign and horoscope for the desired timeframe.
    """
    print('Please enter your first name and date of birth.')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990')

    while True:
        name = input('Name:\n')
        try:
            validate_name(name)
            break
        except TypeError as e:
            print(e)

    while True:
        birth_date = input('Date of Birth (DD/MM/YYYY):\n')
        try:
            validate_date(birth_date)
            break
        except ValueError as e:
            print(e)
            
start_app()