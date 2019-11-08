"""Voyager: a Janeway Journal and Proceedings Crawler"""

import csv

from lxml import etree
import requests


def get_dois_from_csv(csv_file, col=0):
    """Get DOIs from CSV file.

    Parameters
    ----------
    csv_file : str or pathlib.Path
        CSV file to read.
    
    col : int
        Which CSV column to look for DOIs. Default is 0.

    Returns
    -------
    list
    """
    dois = []
    with open(csv_file, "r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        # Discard the header row
        next(reader, None)
        for row in reader:
            dois.append(row[col])

    return dois


def get_article_urls_from_articles_index(collection_url: str) -> list:
    """Expected collection_url to be in the form 'https://{root_url}/{collection_name}/articles'"""
    article_url_xpath = "//div[@class='box article']/a/@href"
    next_page_url_xpath = "//ul[@class='pagination']/li[@class='current']/following-sibling::li[@class='arrow']/a/@href"

    r = requests.get(collection_url)
    collection_index = etree.HTML(r.text)
    article_urls = collection_index.xpath(article_url_xpath)
    next_index_page = collection_index.xpath(next_page_url_xpath)

    while next_index_page:
        print(article_urls)
        r = requests.get(f"{collection_url}{next_index_page[0]}")
        collection_index = etree.HTML(r.text)
        article_urls.extend(collection_index.xpath(article_url_xpath))
        next_index_page = collection_index.xpath(next_page_url_xpath)

    for i, url in enumerate(article_urls):
        article_urls[i] = prepend_url(url)

    return article_urls


def get_article_urls_from_issues_index(collection_url: str) -> list:
    """Expected collection_url to be in the form 'https://{root_url}/{collection_name}/issues'"""
    issue_url_xpath = "//div[@class='box issue']/a/@href"
    next_page_url_xpath = "//ul[@class='pagination']/li[@class='current']/following-sibling::li[@class='arrow']/a/@href"

    r = requests.get(collection_url)
    collection_index = etree.HTML(r.text)
    issue_urls = collection_index.xpath(issue_url_xpath)
    next_issue_page = collection_index.xpath(next_page_url_xpath)

    while next_issue_page:
        r = requests.get(f"{collection_url}{next_issue_page}")
        collection_index = etree.HTML(r.text)
        issue_urls.extend(collection_index.xpath(issue_url_xpath))
        next_issue_page = collection_index.xpath(next_page_url_xpath)

    for i, url in enumerate(issue_urls):
        issue_urls[i] = prepend_url(url)

    article_urls = []
    for issue_url in issue_urls:
        article_urls.extend(get_article_urls_from_articles_index(issue_url))

    return article_urls


def prepend_url(url):
    base_url = "https://www.iastatedigitalpress.com"
    if not url.startswith(base_url):
        url = f"{base_url}{url}"

    return url


def get_article(url):
    r = requests.get(url)
    article = etree.HTML(r.text)

    return article


def get_title(article):
    title_xpath = "//figcaption[@class='orbit-caption']/h3"
    title = article.xpath(title_xpath)[0].text

    return title


def get_full_text_url(article):
    full_text_url_xpath = (
        "//div[@class='section']/h3[text()='Download']/following-sibling::ul/li/a/@href"
    )
    full_text_url = prepend_url(article.xpath(full_text_url_xpath)[0])

    return full_text_url


def get_etrees_from_urls(urls):
    articles = []
    for url in urls:
        articles.append(get_article(url))

    return articles


def get_article_titles_from_etrees(articles):
    titles = []
    for article in articles:
        titles.append(get_title(article))

    return titles


def get_article_titles_from_urls(urls: list) -> list:
    titles = []
    for url in urls:
        article = get_article(url)
        title = get_title(article)
        titles.append(title)

    return titles


def get_article_full_text_urls_from_etrees(articles):
    full_text_urls = []
    for article in articles:
        full_text_urls.append(get_full_text_url(article))

    return full_text_urls


def zip_article_titles_and_urls(titles, urls):
    titles_urls = list(zip(titles, urls))

    return titles_urls


def match_dois_to_urls_by_title(dois_md, titles_urls):
    matches = []
    for doi_md in dois_md:
        for tu in titles_urls:
            if doi_md["title"][0] == tu[0]:
                matches.append((doi_md["DOI"], tu[0], tu[1]))
                continue

    return matches


def find_urls_without_dois_by_title(dois_md, titles_urls):
    unmatches = []
    doi_titles = set()
    web_titles = set()

    for doi_md in dois_md:
        doi_titles.add(doi_md["title"][0])

    for tu in titles_urls:
        web_titles.add(tu[0])

    web_only = web_titles - doi_titles

    web_only_titles_urls = [row for row in titles_urls if row[0] in web_only]

    return web_only_titles_urls


def write_matches_to_csv(matches, csv_file):
    with open(csv_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, dialect="excel")
        for row in matches:
            writer.writerow(row)


def main():
    pass
