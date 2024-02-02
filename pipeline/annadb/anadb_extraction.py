import time
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from pathlib import Path
import csv

def get_git_directory():
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        git_dir = current_dir / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return git_dir.parent
        current_dir = current_dir.parent
    return None


# Initialize Chrome WebDriver using WebDriver Manager
options = webdriver.ChromeOptions()
#options.add_argument("--headless")  # Run Chrome in headless mode
# options.add_argument("--disable-gpu")  # Disable GPU acceleration (may be needed in headless mode)
# driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)

# Open Google News
driver.get("https://www.annaservice.com/isinlookup/login")
time.sleep(2)  # Let the results load

driver.find_element(By.XPATH,'//*[@id="username"]').send_keys('email')
driver.find_element(By.XPATH,'//*[@id="password"]').send_keys('pass')
driver.find_element(By.XPATH,'/html/body/main/section/form/font/font/input[3]').click()
time.sleep(5)
filename = str( get_git_directory() / "data" / "isin.txt") 

with open(filename, 'r') as file:
        row_num =1
        for line in file:
            try:
                ISIN = line.strip()
                print(f"{row_num}. fetching data for {ISIN}")
                driver.find_element(By.XPATH,'//*[@id="isinValue"]').send_keys(ISIN)
                driver.find_element(By.XPATH,'//*[@id="wrapper"]/main/section/form/center/input').click()
                time.sleep(2)
                driver.find_element(By.XPATH,'//*[@id="isinRecordsTable"]/tr/td[1]/a').click()
                time.sleep(2)

                out_isin = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[2]').text
                #Issuer
                issuer = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[3]').text
                #Issuer Desc
                issuer_desc = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[4]').text
                #Currency
                curr =driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[5]').text
                #Int Rate
                int_rate = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[6]').text
                #Maturity Date
                mat_date = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[7]').text
                #FISIN
                fisin = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[8]').text
                #CFI
                cfi = driver.find_element(By.XPATH,'//*[@id="isinDetailTable"]/tbody/tr[2]/td[9]').text

                output_csv = str( get_git_directory() / "data" / "cfi_output.csv") 
                with open(output_csv, "a", newline="", encoding="utf-8") as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow([out_isin, issuer, issuer_desc, curr, int_rate, mat_date, fisin, cfi])
                driver.find_element(By.XPATH,'//*[@id="wrapper"]/main/section/div/center/table/tbody/tr/td/div/center/form/input[2]').click()
                time.sleep(2)
                row_num=row_num+1
            except:
                driver.get('https://www.annaservice.com/isinlookup/search')
                continue
    #//*[@id="username"]
#//*[@id="password"]
#/html/body/main/section/form/font/font/input[3]

driver.get("https://www.annaservice.com/isinlookup/search_detailResult?isin=AT0000A36XD5")
time.sleep(2) 



             
with open(output_csv, "w", newline="", encoding="utf-8") as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["URL", "Keyword", "Status", "timestamp"])


