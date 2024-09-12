# Import neccesary packages for our app
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime as dt
import requests
from bs4 import BeautifulSoup
from kerykeion import AstrologicalSubject, Report, KerykeionException
import pandas as pd
import pickle
import gzip
from timezonefinder import TimezoneFinder
import pytz
import questionary
import textwrap
import shutil
import json
from rich.console import Console

# This section of code is borrowed from the "Love Sandwiches" project
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
    ]

# Define constant variables - also borrowed from "Love Sandwiches" project
CREDS = Credentials.from_service_account_file('creds.json')
SCOPED_CREDS = CREDS.with_scopes(SCOPE)
GSPREAD_CLIENT = gspread.authorize(SCOPED_CREDS)
SHEET = GSPREAD_CLIENT.open('astrology_app')

# Using gzip and pandas to open the compressed dataset and read the data
with gzip.open('assets/datasets/compressed-cities-df.csv.gz', 'rb') as file:
    cities_df = pd.read_csv(file)


def prettify_text(text, style, color, emoji=None):
    """
    Formats text with colors and emojis and displays it
    in the terminal by using rich library.

    Args:
        text (str): Text that is displayed.
        style (str): Style of the text i.e.: bold.
        color (str): The color of the text.
        emoji (str): The emoji displayed. Defaults to None.
    """
    console = Console()
    if emoji:
        console.print(f'[{style} {color}]{text}[/] :{emoji}:')
    else:
        console.print(f'[{style} {color}]{text}[/]')

def warning_text(text):
    """
    Formats error messages and displays it
    in the terminal by using rich library.

    Args:
        text (str): The text that is displayed.
    """
    console = Console()
    console.print(f'[bold red]{text}[/] :warning:')


def start_app(message):
    """
    Starts the app by asking the user to pick multiple options:
    Horoscope, Birth Chart, Compatibility or simply exit the app.

    Args:
        message (str): Message that gets printed in the terminal.
    """
    prettify_text(message, 'bold', 'purple', 'crystal_ball')
    options = ['Horoscope', 'Birth Chart', 'Compatibility', 'Exit']

    # Use Questionary library to provide options for a pleasant UX
    select_option = (questionary.select('Select an option:',
                                        choices=options).ask())

    # Returns a tuple containing the option selected and the function that will initialize
    try:
        if select_option == 'Horoscope':
            return 'Horoscope', horoscope()
        elif select_option == 'Birth Chart':
            return 'Birth Chart', birth_chart()
        elif select_option == 'Compatibility':
            return 'Compatibility', get_compatibility()
        elif select_option == 'Exit':
            prettify_text('Thank you for using AstrologyApp!',
                          'bold',
                          'orange1',
                          'sparkles')
            return None, None
    except (TypeError, ValueError) as e:
        warning_text(f'An error occured while starting the app: {e}')

def validate_name(name):
    """
    Validates name so it can only contain alphabetic characters
    and can't be longer than 50 characters.

    Args:
        name (str): A string containing a name.
    """
    try:
        if not name:
            raise TypeError(warning_text('Name cannot be empty.'))
        elif not name.isalpha():
            raise TypeError(warning_text('Name can only contain alphabetic characters.'))
        elif len(name) >= 50:
            raise TypeError(warning_text('Name must have 50 characters or less.'))
        elif not name[0].isupper():
            raise TypeError(warning_text('Name must start with a capital letter.'))
    except ValueError:
        raise ValueError(warning_text('Invalid name.'))

def validate_date(date):
    """
    Validates date of birth so it is only in DD/MM/YYYY format.

    Args:
        date (obj): The date of birth (DD/MM/YYYY)
    """
    try:
        # Used datetimes' strptime method to validate the birth date
        valid_date = dt.strptime(date, '%d/%m/%Y')
    except ValueError:
        raise ValueError(warning_text('Please enter the date in DD/MM/YYYY format.'))
    return valid_date

def validate_time(time):
    """
    Validates the time of birth so it is 24-hour format (HH:MM)

    Args:
        time (obj): The time of birth (HH:MM)
    """
    try:
        # Used datetimes' strptime method to validate the birth time
        valid_time = dt.strptime(time, '%H:%M')
    except ValueError:
        raise ValueError(warning_text('Please enter the time in HH:MM format.'))
    return valid_time

def validate_location(location):
    """
    Validates the location of birth.

    Args:
        location (str): Location of birth.
    """

    # Iterates through the allowed_characters string to ensure 
    # location input is valid
    allowed_characters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ /-'
    try:
        for char in location:
            if char not in allowed_characters:
                raise TypeError(warning_text("Location can only contain letters, '/' and/or '-'."))
        if not location:
            raise TypeError(warning_text('This field cannot be empty.'))
        elif not location[0].isupper():
            raise TypeError(warning_text('Location name must start with a capital letter.'))
    except TypeError as e:
        warning_text(f'An error occured while validating location: {e}')
    return location


def prompt_user_for_input(prompt, validation_func):
    """
    Prompts user to input their details and then validates it.

    Args:
        prompt (str): Prompt for the input.
        validation_func (func): Validation function.
    """
    while True:
        user_input = input(prompt)
        try:
            validation_func(user_input)
            return user_input
        except (TypeError, ValueError) as e:
            warning_text(f'An error occured while getting input: {e}')


def fetch_coordinates_from_dataset(city, df):
    """
    Gets the longitude and latitude from the cities-df dataset.

    Args:
        city (str): The city/town where the user is born.
        df (obj): The dataset from which the data is extracted from.
    """
    try:
        city_data = df[df['City'].str.lower() == city.lower()]
        # Used pandas' iloc method to extract the lat and long
        lat = city_data.iloc[0]['Latitude']
        long = city_data.iloc[0]['Longitude']
        return lat, long
    except ValueError as e:
        warning_text(f'An error occured while fetching coordinates: {e}')

def fetch_timezone(lat, long):
    """
    Gets the corresponding timezone based on the coordinates given.

    Args:
        lat (float): Latitude of the location.
        long (float): Longitude of the location.

    Returns:
        tz_str (str): Timezone name.
    """
    try:
        # Used TimezoneFinder() from timezonefinder to calculate timezone
        tz = TimezoneFinder()
        tz_str = tz.timezone_at(lat=lat, lng=long)
        if tz_str is None:
            raise ValueError(warning_text('Timezone not found.'))
    except ValueError as e:
        warning_text(f'An error occured while fetching the timezone: {e}')
    return tz_str


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
    try:
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return 'Invalid date'

        # The inspiration for this structure was from the tuple unpacking tutorial
        # on W3Schools and a dev.to article - link in README.md
        zodiac_signs = [((3, 21, 4, 19), 'Aries', 1),
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
    except ValueError as e:
        warning_text(f'An error occured while calculating zodiac sign: {e}')


def get_horoscope(url, timeframe):
    """
    Gets the desired horoscope and formats it from the given URL based on the timeframe.
    This function was created using the BeautifulSoup4 library.

    Args:
        url (str): The URL BeautifulSoup needs to request information from.
        timeframe (str): The timeframe the user chooses for their horoscope.
    """
    try:
        # Used BeautifulSoup and requests code to scrap data and display it
        # credits to W3Resources article and BeautifulSoup4 documentation
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        if timeframe == 'Yearly':
            horoscope_text = soup.find('section', id='personal').p.text
        else:
            horoscope_text = soup.find('div', class_='main-horoscope').p.text
        # This line of code was taken and adapted from a StackOverflow forum page
        # link in README.md
        formatted_text = textwrap.fill(horoscope_text, width=shutil.get_terminal_size().columns)
        return formatted_text
    except Exception as e:
        warning_text(f'An unexpected error occured while requesting data: {e}')

def horoscope():
    """
    Takes input from the user, validates it and returns the user's
    zodiac sign and horoscope for the desired timeframe.
    """
    print('Please enter your first name and date of birth.\n')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990\n')

    name = prompt_user_for_input('\nName:\n', validate_name)
    birth_date = prompt_user_for_input('\nDate of Birth (DD/MM/YYYY):\n',
                                       validate_date)
    valid_date = validate_date(birth_date)

    # Outputs the user's zodiac sign
    zodiac_day = valid_date.day
    zodiac_month = valid_date.month
    zodiac_sign = get_zodiac_sign(zodiac_day, zodiac_month)
    print(f'\nHello, {name}. Your zodiac sign is {zodiac_sign[0]}.\n')

    # Display timeframe options to choose from
    options = ['Daily', 'Weekly', 'Monthly', 'Yearly']
    # Use Questionary library to provide options for a pleasant UX
    select_option = (questionary.select('Please choose the timeframe of your desired horoscope:', choices=options, ).ask())

    timeframes = {'Daily': f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-daily-today.aspx?sign={zodiac_sign[1]}',
                  'Weekly': f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-weekly.aspx?sign={zodiac_sign[1]}',
                  'Monthly': f'https://www.horoscope.com/us/horoscopes/general/horoscope-general-monthly.aspx?sign={zodiac_sign[1]}',
                  'Yearly': f'https://www.horoscope.com/us/horoscopes/yearly/2024-horoscope-{zodiac_sign[0]}.aspx'
                  }

    print(f'\n{select_option} horoscope for {name}, a {zodiac_sign[0]}:\n')
    horoscope_text = get_horoscope(timeframes[select_option], select_option)
    print(horoscope_text)

    # Convert valid_date into json_date so it can be appended to the worksheet - credits to Geeks for Geeks
    # website - article linked in README.md
    # Also used the datetimes' strftime method to display data in a specific way
    str_date = valid_date.strftime('%d/%m/%Y')
    json_date = json.dumps(str_date)

    horoscope_data = [name, json_date, zodiac_sign[0], select_option, horoscope_text]
    start_app('\nTry something else!')
    return horoscope_data

def birth_chart_user_input():
    """
    Prompts the user to input their details for birth chart generation
    """
    print('\nPlease enter your first name:\n')
    name = prompt_user_for_input('\nName:\n', validate_name)
    print('\nPlease enter your date of birth:\n')
    birth_date = prompt_user_for_input('\nDate of Birth (DD/MM/YYYY):\n', validate_date)
    valid_date = validate_date(birth_date)
    print('\nPlease enter your time of birth:\n')
    birth_time = prompt_user_for_input('\nTime of Birth (24-hour format - HH:MM):\n', validate_time)
    valid_time = validate_time(birth_time)
    print('\nPlease enter your location of birth:\n')
    location_city = prompt_user_for_input('\nCity:\n', validate_location)
    location_country = prompt_user_for_input('\nCountry:\n', validate_location)

    return name, valid_date, valid_time, location_city, location_country

def generate_birth_chart(name, valid_date, valid_time, location_city, location_country, lat, long, tz_str):
    """
    Generates the birth chart by using Kerykeion's AstrologicalSubject().

    Args:
        name (str): The user's name.
        valid_date (datetime): The user's date of birth.
        valid_time (datetime): The user's time of birth.
        location_city (str): The user's city of birth.
        location_country (str): The user's country of birth.
        lat (float): The latitude of the location.
        long (float): The longitude of the location.
        tz_str (str): The timezone of the location.
    """
    return AstrologicalSubject(
            name=name,
            year=valid_date.year,
            month=valid_date.month,
            day=valid_date.day,
            hour=valid_time.hour,
            minute=valid_time.minute,
            city=location_city,
            nation=location_country,
            lat=lat,
            lng=long,
            tz_str=tz_str,
            geonames_username='petra66orii'
        )

def zodiac_dictionary(chart):
    """
    Kerykeion library has the zodiac signs abbreviated
    and it would display in the terminal as such. I felt like that would
    affect the UX, so I decided to create a dictionary function that would fix this.

    Args:
        chart (AstrologicalSubject): The user's birth chart.
    """
    zodiac_dict = {'Ari': 'Aries',
                'Tau': 'Taurus',
                'Gem': 'Gemini',
                'Can': 'Cancer',
                'Leo': 'Leo',
                'Vir': 'Virgo',
                'Lib': 'Libra',
                'Sco': 'Scorpio',
                'Sag': 'Sagittarius',
                'Cap': 'Capricorn',
                'Aqu': 'Aquarius',
                'Pis': 'Pisces'
                }

    # Assign variables using AstrologicalSubject() methods
    signs = {'sun_sign': zodiac_dict.get(chart.sun.sign),
             'moon_sign': zodiac_dict.get(chart.moon.sign),
             'rising_sign': zodiac_dict.get(chart.first_house.sign),
             'mercury_sign': zodiac_dict.get(chart.mercury.sign),
             'venus_sign': zodiac_dict.get(chart.venus.sign),
             'mars_sign': zodiac_dict.get(chart.mars.sign),
             'jupiter_sign': zodiac_dict.get(chart.jupiter.sign),
             'saturn_sign': zodiac_dict.get(chart.saturn.sign),
             'uranus_sign': zodiac_dict.get(chart.uranus.sign),
             'neptune_sign': zodiac_dict.get(chart.neptune.sign),
             'pluto_sign': zodiac_dict.get(chart.pluto.sign)
             }
    return signs 

def print_first_signs(name, chart, signs):
    """
    Prints a small message for the user outputting the three main signs.

    Args:
        name (str): Name of the user.
        chart (AstrologicalSubject): User's birth chart.
        signs (dict): The user's signs.
    """
    print(f'\nHello, {name}. Your Sun sign is {signs['sun_sign']} {chart.sun.emoji}.\n')
    print(f'Your Moon sign is {signs['moon_sign']} {chart.moon.emoji}.\n')
    print(f'Your Rising sign is {signs['rising_sign']} {chart.first_house.emoji}.\n')

def save_birth_chart_data(name, valid_date, valid_time, location_city, location_country, signs):
    """
    Saves the birth chart data and prepares it to be updated in the worksheet.

    Args:
        name (str): The user's name.
        valid_date (datetime): The user's date of birth.
        valid_time (datetime): The user's time of birth.
        location_city (str): User's city of birth.
        location_country (str): User's country of birth.
        signs (dict): User's zodiac signs.
    """
    
    # Convert valid_date into json_date so it can be appended to the worksheet 
    # credits to Geeks for Geeks website - article linked in README.md
    # Also used the datetimes' strftime method to display data in a specific way
    str_date = valid_date.strftime('%d/%m/%Y')
    json_date = json.dumps(str_date)
    str_time = valid_time.strftime('%H:%M')
    json_time = json.dumps(str_time)

    
    return [name,
            json_date,
            json_time,
            location_city,
            location_country,
            signs['sun_sign'],
            signs['moon_sign'],
            signs['rising_sign'],
            signs['mercury_sign'],
            signs['venus_sign'],
            signs['mars_sign'],
            signs['jupiter_sign'],
            signs['saturn_sign'],
            signs['uranus_sign'],
            signs['neptune_sign'],
            signs['pluto_sign']
            ]


def birth_chart():
    """
    Gets the birth chart and displays it in the terminal
    """
    
    # Initialize birth_chart_data
    birth_chart_data = None
    # Fetch the user input
    name, valid_date, valid_time, location_city, location_country = birth_chart_user_input()

    try:

        lat, long = fetch_coordinates_from_dataset(location_city, cities_df)
        tz_str = fetch_timezone(lat, long)

        # Generate the chart
        chart = generate_birth_chart(name=name, 
                                     valid_date=valid_date,
                                     valid_time=valid_time,
                                     location_city=location_city,
                                     location_country=location_country,
                                     lat=lat,
                                     long=long,
                                     tz_str=tz_str)
        # Get the zodiac dictionary to dislay the full zodiac sign
        signs = zodiac_dictionary(chart=chart)
        # Print a message for the user
        print_first_signs(name=name, chart=chart, signs=signs)

        # Use Kerykeion's Report() to generate and display the chart 
        report = Report(chart)
        report.print_report()
        # Save the data
        birth_chart_data = save_birth_chart_data(name=name,
                                                 valid_date=valid_date,
                                                 valid_time=valid_time,
                                                 location_city=location_city,
                                                 location_country=location_country,
                                                 signs=signs)

    except KerykeionException as e:
        print(f"An error occurred: {e}\n Please try again.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    start_app('\nTry something else!')
    return birth_chart_data

def get_compatibility():
    """
    Gets the compatibility between two zodiac signs and displays it
    """
    print("Find out if you're compatible!\n")
    print('Please fill out the necessary information:\n')
    print('Example:\n Name: Gerry \n Date of Birth: 20/06/1990\n')

    print('\nPlease enter your first name:\n')
    name1 = prompt_user_for_input('\nName:\n', validate_name)
    print('\nPlease enter their first name:\n')
    name2 = prompt_user_for_input('\nName:\n', validate_name)

    print('\nPlease enter your date of birth:\n')
    birth_date1 = prompt_user_for_input('\nDate of Birth (DD/MM/YYYY):\n', validate_date)
    valid_date1 = validate_date(birth_date1)
    print('\nPlease enter their birth date:\n')
    birth_date2 = prompt_user_for_input('\nDate of Birth (DD/MM/YYYY):\n', validate_date)
    valid_date2 = validate_date(birth_date2)

    zodiac_day1 = valid_date1.day
    zodiac_month1 = valid_date1.month
    zodiac_day2 = valid_date2.day
    zodiac_month2 = valid_date2.month
    zodiac_sign1 = get_zodiac_sign(zodiac_day1, zodiac_month1)
    zodiac_sign2 = get_zodiac_sign(zodiac_day2, zodiac_month2)
    print(f"\nHello, {name1}. Your zodiac sign is {zodiac_sign1[0]},\nand {name2}'s zodiac sign is {zodiac_sign2[0]}.\n")
    print("Let's see your compatibility!")

    # Used BeautifulSoup and requests code to scrap data and display it 
    # credits to W3Resources article and BeautifulSoup4 documentation
    url = f'https://www.horoscope.com/love/compatibility/{zodiac_sign1[0]}-{zodiac_sign2[0]}'
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    horoscope_text = soup.find('div', class_='module-skin').p.text
    formatted_text = textwrap.fill(horoscope_text, width=shutil.get_terminal_size().columns)
    print(formatted_text)

    # Convert valid_date into json_date so it can be appended to the worksheet - credits to Geeks for Geeks
    # website - article linked in README.md
    # Also used the datetimes' strftime method to display data in a specific way
    str_date1 = valid_date1.strftime('%d/%m/%Y')
    json_date1 = json.dumps(str_date1)
    str_date2 = valid_date2.strftime('%d/%m/%Y')
    json_date2 = json.dumps(str_date2)

    compatibility_data = [name1,
                          json_date1,
                          zodiac_sign1[0],
                          name2,
                          json_date2,
                          zodiac_sign2[0],
                          formatted_text
                          ]

    start_app('\nTry something else!')
    return compatibility_data


def update_worksheet(data, worksheet):
    """
    Updates the worksheet with the provided data.
    Using gspread library for this function.

    Args:
        data (obj): Data provided from the user.
        worksheet (obj): Where the data gets stored.
    """
    worksheet.append_row(data)


def main_program():
    """
    Initiates the entire program
    """

    # Define the sheet variables using gspread's methods
    horoscope_sheet = SHEET.worksheet('horoscope')
    birth_chart_sheet = SHEET.worksheet('birth_chart')
    compatibility_sheet = SHEET.worksheet('compatibility')

    option, data = start_app('Welcome to AstrologyApp!')
    try:
        if option == 'Horoscope' and data:
            update_worksheet(data, horoscope_sheet)
        elif option == 'Birth Chart' and data:
            update_worksheet(data, birth_chart_sheet)
        elif option == 'Compatibility' and data:
            update_worksheet(data, compatibility_sheet)
    except (TypeError, ValueError) as e:
        print(f'An error occured while updating the worksheet: {e}')


main_program()