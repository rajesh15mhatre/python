import requests
from bs4 import BeautifulSoup
from pathlib import Path

DATA = Path.home() / "data" 
def search_google_news(keyword):
    news_list = []
    base_url = 'https://news.google.com'
    search_url = f'{base_url}/search?q="{keyword}"when:1h&hl=en-US&gl=US&ceid=US%3Aen'
    # Fetching the search results page
    response = requests.get(search_url)
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
    return news_list

def retrieve_news_pages(keyword):
    news = search_google_news(keyword)
    return news

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

def main():
    filename = str( get_git_directory() / "data" / "companies.txt")  # Replace with the path to your text file
    with open(filename, 'r') as file:
        for line in file:
            keyword = line.strip()  # Remove leading/trailing whitespace and newline characters
            news_pages = retrieve_news_pages(keyword)
            # Displaying the news articles
            for news in news_pages:
                print(f'Title: {news["title"]}')
                print(f'Link: {news["link"]}')
                print(f'Source: {news["source"]}')
                print(f'Timestamp: {news["timestamp"]}')
                # print(f'Description: {news["description"]}')
                print('---')
     

if __name__ == "__main__":
    main()
