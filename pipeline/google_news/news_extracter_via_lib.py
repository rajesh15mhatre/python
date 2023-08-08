from gnewsclient import gnewsclient


def main():
    client = gnewsclient.NewsClient(language='english', location='US', topic='SAMSUNG', max_results=30)
    client.print_news()

if __name__ == "__main__":
    main()