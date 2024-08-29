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
    return valid_date

def get_zodiac_sign(day, month):
    """
    Gets the zodiac sign of the user based on the day and month inputs.
    """
    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return 'Aquarius'
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return 'Pisces'
    elif (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return 'Aries'
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return 'Taurus'
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return 'Gemini'
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return 'Cancer'
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return 'Leo'
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return 'Virgo'
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return 'Libra'
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return 'Scorpio'
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return 'Sagittarius'
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return 'Capricorn'
    else:
        return 'Invalid date'

def horoscope():
    """
    Takes input from the user, validates it and returns the user's 
    zodiac sign and horoscope for the desired timeframe.
    """
    print('Please enter your first name and date of birth.\n')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990\n')

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
            valid_date = validate_date(birth_date)
            break
        except ValueError as e:
            print(e)
            
start_app()