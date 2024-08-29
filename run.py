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

# Define constant variables 
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
    Validates date of birth so it is only in DD/MM/YYYY format
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
    # Between 20 Jan and 18 Feb: Aquarius
    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return 'Aquarius'
    # Between 19 Feb and 20 Mar: Pisces
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return 'Pisces'
    # Between 21 Mar and 19 Apr: Aries
    elif (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return 'Aries'
    # Between 20 Apr and 20 May: Taurus
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return 'Taurus'
    # Between 21 May and 20 Jun: Gemini
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return 'Gemini'
    # Between 21 Jun and 22 Jul: Cancer
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return 'Cancer'
    # Between 23 Jul and 22 Aug: Leo
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return 'Leo'
    # Between 23 Aug and 22 Sep: Virgo
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return 'Virgo'
    # Between 23 Sep and 22 Oct: Libra
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return 'Libra'
    # Between 23 Oct and 21 Nov: Scorpio
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return 'Scorpio'
    # Between 22 Nov and 21 Dec: Sagittarius
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return 'Sagittarius'
    # Between 22 Dec and 19 Jan: Capricorn
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

    # Validate the name 
    while True:
        name = input('Name:\n')
        try:
            validate_name(name)
            break
        except TypeError as e:
            print(e)

    # Validate the birthdate
    while True:
        birth_date = input('Date of Birth (DD/MM/YYYY):\n')
        try:
            valid_date = validate_date(birth_date)
            break
        except ValueError as e:
            print(e)
    
    # Outputs the user's zodiac sign
    zodiac_day = valid_date.day
    zodiac_month = valid_date.month
    zodiac_sign = get_zodiac_sign(zodiac_day, zodiac_month)
    print(f'Hello, {name}. Your zodiac sign is {zodiac_sign}.\n')

    options = ['Daily', 'Weekly', 'Monthly', 'Yearly']
    select_option = (questionary.select('Please choose the timeframe of your desired horoscope:', choices=options, ).ask())

    if select_option == 'Daily':
        print(f'Daily horoscope for {name}, a {zodiac_sign}:')
    elif select_option == 'Weekly':
        print(f'Weekly horoscope for {name}, a {zodiac_sign}:')
    elif select_option == 'Monthly':
        print(f'Monthly horoscope for {name}, a {zodiac_sign}:')
    elif select_option == 'Yearly':
        print(f'Yearly horoscope for {name}, a {zodiac_sign}:')
            
start_app()