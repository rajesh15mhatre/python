import time
import csv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By


# List of company names and keywords
company_names = ["Google", "Apple", "Microsoft"]  # Add more company names as needed
keywords_to_search = ["technology", "innovation", "earnings"]

# Initialize Chrome WebDriver using WebDriver Manager
options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # Run Chrome in headless mode
# options.add_argument("--disable-gpu")  # Disable GPU acceleration (may be needed in headless mode)
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)


# Open Google News
driver.get("https://news.google.com")

# Function to search for company names and check keywords in articles
def search_and_check_keywords(company_name, keywords):
    base_url = 'https://news.google.com'
    search_url = f'{base_url}/search?q="{company_name}"when:{"1h"}&hl=en-US&gl=US&ceid=US%3Aen'
    driver.get(search_url)
    time.sleep(2)  # Let the results load
    
    results = driver.find_elements(By.CSS_SELECTOR, ".xrnccd")
    for result in results:
        title = result.find_element(By.CSS_SELECTOR, "h3").text
        link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        timestamp = result.find_element(By.CSS_SELECTOR, "time").get_attribute("datetime")
        
        # Visit the article URL
        # driver.get(link)

        # Open the result link in a new tab
        ActionChains(driver).key_down(Keys.CONTROL).click(result).key_up(Keys.CONTROL).perform()
        
        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[-1])
        
        # Get the article content
        # article = driver.find_element(By.CSS_SELECTOR, "article")
        # article_text = article.text

        time.sleep(4)  # Let the article load
       # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))
        
        # Locate the article content using a different selector
        # article = driver.find_element(By.CSS_SELECTOR, "article")
        # article_text = article.text
        # Find all elements containing text
        text_elements =  driver.execute_script("return document.body.textContent")

        # Extract and print the visible text
        article_text = "\n".join(element.strip() for element in text_elements if element.strip())
        
        # Check if any of the keywords are present in the article
        keyword_found = any(keyword in article_text for keyword in keywords)
        
        # Log the results in CSV
        with open("news_results.csv", "a", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow([company_name, title, driver.current_url, timestamp, keyword_found])
        # Close the tab and switch back to the main tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

# Loop through company names and search for keywords
for company in company_names:
    search_and_check_keywords(company, keywords_to_search)

# Close the WebDriver
driver.quit()
