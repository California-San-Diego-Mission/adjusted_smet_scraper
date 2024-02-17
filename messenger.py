#pylint: disable=line-too-long
"""Selenium client for interacting with Facebook messenger"""

import json
import time
from os import getenv
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

DROPIN_URL = "https://www.messenger.com/t/7570004799678379"

class MessengerClient():
    """Client to send messages via messenger, using Selenium"""
    def __init__(self):
        load_dotenv()

        option = Options()
        option.add_argument("--disable-infobars")
        option.add_argument("start-maximized")
        option.add_argument("--disable-extensions")
        option.add_argument("--headless")
        option.add_argument("headless")
        option.add_argument("--window-size=1920,1080")
        option.add_argument("--disable-gpu")
        option.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

        self.browser = webdriver.Firefox(options=option)
        self.email = getenv("FACEBOOK_EMAIL")
        self.password = getenv("FACEBOOK_PASSWORD")

    def login(self):
        """
        Logs into Facebook and Messenger, resetting cookies
        """
        self.browser.get("https://messenger.com/")

        # Wait for the email and pass inputs to load
        email_input = WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable((By.ID, 'email')))
        password_input = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, 'pass')))
        login_button = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, 'loginbutton')))
        self.screenshot()

        email_input.send_keys(self.email)
        password_input.send_keys(self.password)
        login_button.click()

    def screenshot(self):
        """
        Takes a screenshot and saves it to sel.png
        """
        self.browser.save_screenshot('sel.png')

    def save_cookies(self):
        """
        Saves the cookies to messenger.json
        """
        cookie_list = self.browser.get_cookies()
        with open('messenger.json', 'w', encoding='utf-8') as f:
            json.dump(cookie_list, f, indent=4)

    def load_cookies(self):
        """
        Loads the cookies from the json
        """
        self.browser.get('https://messenger.com')
        with open('messenger.json', 'r', encoding='utf-8') as f:
            cookie_list = json.load(f)
            for cookie in cookie_list:
                self.browser.add_cookie(cookie)
        self.browser.refresh()

    def send_message(self, message):
        """
        Sends a message into the drop in chat
        """
        # Make sure the URL is correct
        if self.browser.current_url != DROPIN_URL:
            self.browser.get(DROPIN_URL)
            print("Navigated to dropin URL, sleeping now...")
            time.sleep(10)


        # Get the bar
        chat_bar = self.browser.find_element(By.XPATH, '//div[contains(@class, "xzsf02u x1a2a7pz x1n2onr6 x14wi4xw x1iyjqo2 x1gh3ibb xisnujt xeuugli x1odjw0f notranslate")]')

        # Estimate how long the message will take to send
        print(f"Message send ETA: {len(message) / 100} seconds")

        # Send the keys one at a time
        for char in message:
            chat_bar.send_keys(char)
            time.sleep(0.01)

        # Send the enter key
        chat_bar.send_keys(Keys.RETURN)
