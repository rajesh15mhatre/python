#!/usr/bin/env python
"""
This python script ferch gooogle news search result for provided keyword
activate environment before running script to use proper env and run as a module

Usage: python -m pipeline.google_news.news_extracter

Options:
  -h --help          Show this screen.
  --timeframe=<>     time frame for search result can be 1h, 1d,1y [default: 1h]
  --filter_result    Filters result if True [Default:False]
"""
import re
import csv
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import yaml
from pipeline.utils import utils
import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException
from datetime import datetime

DATA = Path.home() / "data" 

# Initialize Chrome WebDriver using WebDriver Manager
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)
# Set the implicit wait timeout (waits for elements to appear)
#driver.implicitly_wait(2)  # 10 seconds
# Set the script timeout (waits for JavaScript to execute)
#driver.set_script_timeout(3)  # 10 seconds
# Set the page load timeout to 2 seconds
driver.set_page_load_timeout(10)


def get_article(result_url):
    try:
       driver.get(result_url)
    except TimeoutException:
        print(f"Page load timed out for {result_url}")

        text_elements =  driver.execute_script("return document.body.textContent")
    time.sleep(2)
    text_elements =  driver.execute_script("return document.body.textContent")
    return driver.current_url, text_elements

def load_config(config_file):
    with open(config_file, 'r') as file:
        config_data = yaml.safe_load(file)
    return config_data


def search_google_news(google_keyword, time_frame, m_n_a_keywords, csv_writer):
    news_list = []
    base_url = 'https://news.google.com'
    search_url = f'{base_url}/search?q="{google_keyword}"when:{time_frame}&hl=en-US&gl=US&ceid=US%3Aen'
    # Fetching the search results page
    response = requests.get(search_url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extracting news articles from the search results
    articles = soup.find_all('article')
    # TODO: add page scroll as page number are not available
    for article in articles:
        title = article.find('h3').text
        link = base_url + article.find('a')['href'][1:]
        source = article.find('img', class_="tvs3Id tvs3Id lqNvvd lITmO WfKKme")['alt']
        timestamp = article.find('time')['datetime']
        #description = article.find('div', class_='Da10Tb T4OwTb').text

        news_list.append({
            'title': title,
            'link': link,
            'source': source,
            'timestamp': timestamp,
        })
        try:
            news_url, news_text = get_article(link.strip())
            for keyword in m_n_a_keywords:
                # Replace spaces with any character pattern (dot)
                keyword_pattern = re.sub(r'\s', '.', keyword)
                pattern = re.compile(keyword_pattern, re.IGNORECASE)

                if re.search(pattern, news_text):
                    print(f"Keyword '{keyword}' found on page: {news_url}")
                    if csv_writer:
                        csv_writer.writerow([news_url, keyword, "Found", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                else:
                    if csv_writer:
                        print(f"{keyword} not found in - {news_url}")
                        csv_writer.writerow([news_url, keyword, "Not Found", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        except Exception as e:
            if csv_writer:
                csv_writer.writerow([link, "N/A", f"An error occurred while processing: {e}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            print(f"An error occurred while processing {news_url}: {e}")

    return news_list

def get_project_root():
    current_dir = Path.cwd()
    return current_dir.parents[len(current_dir.parents) - 1]


def get_git_directory():
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        git_dir = current_dir / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return git_dir.parent
        current_dir = current_dir.parent
    return None

def main(): # time_frame='1h', filter_result=False
    filename = str( get_git_directory() / "data" / "companies.txt")  # Replace with the path to your text file
    # Provide the path to your config.yml file
    config_file = str(get_git_directory() / "config" / "config.yml")
    # result csv
    output_csv =  str( utils.get_git_directory() / "data" / "google_search_logs.csv")
    # Keyword File
    keyword_file_path =  str( utils.get_git_directory() / "data" / "m_n_a_keywards.txt")  
    # Load values from the config file
    config_values = load_config(config_file)

    # Load Keywords:
    with open(keyword_file_path, "r") as file:
        keywords = file.readlines()

    # Access the values and store them in variables
    time_frame = config_values.get('time_frame')
    filter_result = config_values.get('filter_result')
    

    with open(filename, 'r') as file:
        with open(output_csv, "w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["URL", "Keyword", "Status", "timestamp"])
            
            for line in file:
                company = line.strip()  # Remove leading/trailing whitespace and newline characters
                print(f"Searching news for {company}")
                news_pages = search_google_news(company, time_frame, keywords, csv_writer)
                # Displaying the news articles
                for news in news_pages:
                    print(f'Keyword:{company}')
                    print(f'Title: {news["title"]}')
                    print(f'Link: {news["link"]}')
                    print(f'Source: {news["source"]}')
                    print(f'Timestamp: {news["timestamp"]}')
                    # print(f'Description: {news["description"]}')
                    if filter_result:
                        print('news filtered')     
    driver.quit()
     

if __name__ == "__main__":
    main()
