"""
This python script search provided keywords in provided list of wenbsits recursilvley or single sreach based on parameter 
activate environment before running script to use proper env and run as a module

Usage: python -m pipeline.domain_search.domain_search 

"""

import re
import requests
import csv
import pipeline.utils.utils as util
from datetime import datetime


def crawl_website(url, keyword_list, base_url, visited_urls=None, csv_writer=None, is_recursive=False):
    if visited_urls is None:
        visited_urls = set()

    # Check if the URL has already been visited to avoid infinite loops
    if url in visited_urls:
        return

    try:
        # Send a GET request to the URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        visited_urls.add(url)

        if response.status_code == 200:
            for keyword in keyword_list:
                # Replace spaces with any character pattern (dot)
                keyword_pattern = re.sub(r'\s', '.', keyword)
                pattern = re.compile(keyword_pattern, re.IGNORECASE)

                if re.search(pattern, response.text):
                    print(f"Keyword '{keyword}' found on page: {url}")
                    if csv_writer:
                        csv_writer.writerow([url, keyword, "Found", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                else:
                    if csv_writer:
                        csv_writer.writerow([url, keyword, "Not Found", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

            # Find all the internal links on the page
            internal_links = re.findall(r'href=[\'"]?([^\'" >]+)', response.text)

            # Recursively crawl the internal links of the same domain
            for link in internal_links:
                if link.startswith('/'):
                    # Handle relative URLs
                    new_url = f"{base_url}{link}"
                else:
                    new_url = link

                if base_url in new_url and is_recursive :
                    # Recursive call to crawl the new URL
                    crawl_website(new_url, keyword_list, base_url, visited_urls, csv_writer)
        else:
            if csv_writer:
                csv_writer.writerow([url, "N/A", f"Failed to retrieve the page, Status Code: {response.status_code}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            print(f"Failed to retrieve the page: {url}, Status Code: {response.status_code}")
    except Exception as e:
        if csv_writer:
            csv_writer.writerow([url, "N/A", f"An error occurred while processing: {e}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        print(f"An error occurred while processing {url}: {e}")

def main():
    domain_list_file = str( util.get_git_directory() / "data" / "domain_search" / "website_list.txt")  # Path to the test file containing website URLs, one per line
    keyword_list = ["value Creation", "growth equity", "digitalization"]  # List of keywords to search for using regex
    output_csv =  str( util.get_git_directory() / "data" / "domain_search" / "website_logs.csv")     # Path to the output CSV file

    with open(domain_list_file, "r") as file:
        websites = file.readlines()

    with open(output_csv, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["URL", "Keyword", "Status", "timestamp"])

        for website in websites:
            crawl_website(website.strip(), keyword_list, website.strip(), csv_writer=csv_writer, is_recursive=False)

if __name__ == "__main__":
    main()