# Import neccesary packages for our app
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime as dt
import requests
from bs4 import BeautifulSoup
from kerykeion import AstrologicalSubject, Report, KerykeionChartSVG
import questionary
import textwrap
import shutil

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
    options = ['Horoscope', 'Birth Chart', 'Compatibility']

    select_option = (questionary.select('Select an option:', choices=options).ask())

    if select_option == 'Horoscope':
        horoscope()
    elif select_option == 'Birth Chart':
        birth_chart()
    elif select_option == 'Compatibility':
        get_compatibility()

def validate_name(name):
    """
    Validates name so it can only contain alphabetic characters 
    and can't be longer than 50 characters.

    Args: 
        name (str): A string containing a name. 
    """
    try:
        if not name:
            raise TypeError('Name cannot be empty.')
        elif not name.isalpha():
            raise TypeError('Invalid name. Name can only contain alphabetic characters.')
        elif len(name) >= 50:
            raise TypeError('Invalid name. Name must have 50 characters or less.')
        elif not name[0].isupper():
            raise TypeError('Name must start with a capital letter.')
    except ValueError:
        raise ValueError('Invalid Name.')

def validate_date(date):
    """
    Validates date of birth so it is only in DD/MM/YYYY format.

    Args:
        date (obj): The date of birth (DD/MM/YYYY)
    """
    try:
        valid_date = dt.strptime(date, '%d/%m/%Y')
    except ValueError:
        raise ValueError('Invalid date. Please enter the date in DD/MM/YYYY format.')
    return valid_date

def validate_time(time):
    """
    Validates the time of birth so it is 24-hour format (HH:MM)

    Args:
        time (obj): The time of birth (HH:MM)
    """
    try:
        valid_time = dt.strptime(time, '%H:%M')
    except ValueError:
        raise ValueError('Invalid time. Please enter the time in 24-hour HH:MM format.')
    return valid_time

def prompt_user_for_name():
    """
    Prompts user to input their name and then validates it.
    """
    while True:
        name = input('Name:\n')
        try:
            validate_name(name)
            break
        except TypeError as e:
            print(e)
    return name

def prompt_user_for_date():
    """
    Prompts user to input their date of birth and validates it.
    """
    while True:
        birth_date = input('Date of Birth (DD/MM/YYYY):\n')
        try:
            valid_date = validate_date(birth_date)
            break
        except ValueError as e:
            print(e)
    return valid_date

def prompt_user_for_time():
    """
    Prompts user to input their time of birth and validates it.
    """
    while True:
        birth_time = input('Time of Birth (24-hour format - HH:MM):\n')
        try:
            valid_time = validate_time(birth_time)
            break
        except ValueError as e:
            print(e)
    return valid_time

def get_zodiac_sign(day, month):
    """
    Returns a tuple containing the user's zodiac sign 
    and its order in the zodiac list based on the day and month inputs.
    Inner tuple contains the corresponding start months and days, end months and end days
    respectively for each zodiac sign, followed by sign name and order in its list.

    Args:
        day (int): Day of the month.
        month (int): Months of the year.

    Returns:
        zodiac_sign (tuple): Returns a tuple containing the zodiac name
        and order on the standard list.
    """

    # Validate the date within the function
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return 'Invalid date'

    zodiac_signs = [
    ((3, 21, 4, 19), 'Aries', 1),
    ((4, 20, 5, 20), 'Taurus', 2),
    ((5, 21, 6, 20), 'Gemini', 3),
    ((6, 21, 7, 22), 'Cancer', 4),
    ((7, 23, 8, 22), 'Leo', 5),
    ((8, 23, 9, 22), 'Virgo', 6),
    ((9, 23, 10, 22), 'Libra', 7),
    ((10, 23, 11, 21), 'Scorpio', 8),
    ((11, 22, 12, 21), 'Sagittarius', 9),
    ((12, 22, 1, 19), 'Capricorn', 10),
    ((1, 20, 2, 18), 'Aquarius', 11),
    ((2, 19, 3, 20), 'Pisces', 12)
    ]

    for (start_month, start_day, end_month, end_day), sign, order in zodiac_signs:
        if (month == start_month and day >= start_day) or (month == end_month and day <= end_day):
            return sign, order

    return 'Invalid date'


def get_horoscope(url, timeframe):
    """
    Gets the desired horoscope and formats it from the given URL based on the timeframe.
    This function was created using the BeautifulSoup4 library.

    Args:
        url (str): The URL BeautifulSoup needs to request information from.
        timeframe (str): The timeframe the user chooses for their horoscope.  
    """
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    if timeframe == 'Yearly':
        horoscope_text = soup.find('section', id='personal').p.text
    else:
        horoscope_text = soup.find('div', class_='main-horoscope').p.text
    # This line of code was taken and adapted from a StackOverflow forum page - link in README.md
    formatted_text = textwrap.fill(horoscope_text, width=shutil.get_terminal_size().columns)
    return formatted_text

def horoscope():
    """
    Takes input from the user, validates it and returns the user's 
    zodiac sign and horoscope for the desired timeframe.
    """
    print('Please enter your first name and date of birth.\n')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990\n')

    name = prompt_user_for_name()
    valid_date = prompt_user_for_date()
    
    # Outputs the user's zodiac sign
    zodiac_day = valid_date.day
    zodiac_month = valid_date.month
    zodiac_sign = get_zodiac_sign(zodiac_day, zodiac_month)
    print(f'Hello, {name}. Your zodiac sign is {zodiac_sign[0]}.\n')

    # Display timeframe options to choose from
    options = ['Daily', 'Weekly', 'Monthly', 'Yearly']
    select_option = (questionary.select('Please choose the timeframe of your desired horoscope:', choices=options, ).ask())

    if select_option == 'Daily':
        print(f'Daily horoscope for {name}, a {zodiac_sign[0]}:\n')
        url_daily = f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign={zodiac_sign[1]}'
        horoscope_text = get_horoscope(url_daily, 'Daily')
        print(horoscope_text)
    elif select_option == 'Weekly':
        print(f'Weekly horoscope for {name}, a {zodiac_sign[0]}:\n')
        url_weekly = f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-weekly.aspx?sign={zodiac_sign[1]}'
        horoscope_text = get_horoscope(url_weekly, 'Weekly')
        print(horoscope_text)
    elif select_option == 'Monthly':
        print(f'Monthly horoscope for {name}, a {zodiac_sign[0]}:\n')
        url_monthly = f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-monthly.aspx?sign={zodiac_sign[1]}'
        horoscope_text = get_horoscope(url_monthly, 'Monthly')
        print(horoscope_text)
    elif select_option == 'Yearly':
        print(f'Yearly horoscope for {name}, a {zodiac_sign[0]}:\n')
        url_yearly = f'https://www.horoscope.com/us/horoscopes/yearly/2024-horoscope-{zodiac_sign[0]}.aspx'
        horoscope_text = get_horoscope(url_yearly, 'Yearly')
        print(horoscope_text)

def birth_chart():
    """
    Gets the birth chart and displays it in the terminal
    """
    name = prompt_user_for_name()
    valid_date = prompt_user_for_date()
    print('Please enter your time of birth:\n')
    valid_time = prompt_user_for_time()

    print('Birth chart coming soon!')

def get_compatibility():
    """
    Gets the compatibility between two zodiac signs and displays it
    """
    print("Find out if you're compatible!\n")
    print('Please fill out the necessary information:\n')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990\n')

    print('Please enter your first name:\n')
    name1 = prompt_user_for_name()
    print('Please enter their first name:\n')
    name2 = prompt_user_for_name()

    print('Please enter your date of birth:\n')
    valid_date1 = prompt_user_for_date()
    print('Please enter their birth date:\n')
    valid_date2 = prompt_user_for_date()

    zodiac_day1 = valid_date1.day
    zodiac_month1 = valid_date1.month
    zodiac_day2 = valid_date2.day
    zodiac_month2 = valid_date2.month
    zodiac_sign1 = get_zodiac_sign(zodiac_day1, zodiac_month1)
    zodiac_sign2 = get_zodiac_sign(zodiac_day2, zodiac_month2)
    print(f"Hello, {name1}. Your zodiac sign is {zodiac_sign1[0]},\nand {name2}'s zodiac sign is {zodiac_sign2[0]}.\n")
    print("Let's see your compatibility!")

    url = f'https://www.horoscope.com/love/compatibility/{zodiac_sign1[0]}-{zodiac_sign2[0]}'
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    horoscope_text = soup.find('div', class_='module-skin').p.text
    formatted_text = textwrap.fill(horoscope_text, width=shutil.get_terminal_size().columns)
    print(formatted_text)


start_app()