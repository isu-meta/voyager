"""Voyager: a Janeway Journal and Proceedings Crawler"""

import csv
import re

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
        r = requests.get(f"{collection_url}{next_index_page[0]}")
        collection_index = etree.HTML(r.text)
        article_urls.extend(collection_index.xpath(article_url_xpath))
        next_index_page = collection_index.xpath(next_page_url_xpath)

    for i, url in enumerate(article_urls):
        article_urls[i] = prepend_url(url)

    return article_urls


def get_article_urls_from_issue(issue_url: str) -> list:
    """Expected issue_url to be in the form 'https://{root_url}/{collection_name}/issue/{issue_id}/info/"""
    article_url_xpath = "//div[@class='box article']/a/@href"
    next_page_url_xpath = "//ul[@class='pagination']/li[@class='current']/following-sibling::li[@class='arrow']/a/@href"

    r = requests.get(issue_url)
    issue_index = etree.HTML(r.text)

    article_urls = issue_index.xpath(article_url_xpath)
    next_issue_page = issue_index.xpath(next_page_url_xpath)

    while next_issue_page:
        r = requests.get(f"{issue_url}{next_issue_page[0]}")
        issue_index = etree.HTML(r.text)
        article_urls.extend(issue_index.xpath(article_url_xpath))
        next_issue_page = issue_index.xpath(next_page_url_xpath)

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


def get_contributors(article):
    # Not all publications list authors the same way.
    # This XPath works for ITAA and MMB
    contributors_xpath1 = "//span[@itemprop='author']/text()"
    # This XPath works for AHAC
    contributors_xpath2 = "//h4[text()='Authors']/following-sibling::ul/li/text()"

    contributors = [c.strip() for c in article.xpath(contributors_xpath1) if c.strip() != '']

    if not contributors:
        contributors = article.xpath(contributors_xpath2)

    return contributors


def get_doi(article):
    doi_xpath = "//div[@id='article']/p[strong/text()='How to Cite:']/a/@href"
    try:
        doi = article.xpath(doi_xpath)[0]
    except IndexError:
        doi = ""
        
    return doi


def get_citation_text(article):
    citation_xpath = "string(//p[strong/text() = 'How to Cite:'])"
    citation_xpath2 = "string(//p[strong/text() = 'How to Cite:']/following-sibling::p)"
    
    citation_text = article.xpath(citation_xpath)

    if citation_text.strip() == "How to Cite:":
        citation_text = article.xpath(citation_xpath2)

    return citation_text

def _extract_value_from_citation_text(raw_text, pattern):
    try:
        return pattern.search(raw_text).groups()[0]
    except AttributeError:
        return ""


def get_publication_year(article):
    year_p = re.compile(r"\((\d\d\d\d)\)")
    raw_text = get_citation_text(article)
    return _extract_value_from_citation_text(raw_text, year_p)


def get_volume_number(article):
    volume_p = re.compile(r"\. (\d+)\(\d+\)\.")
    raw_text = get_citation_text(article)
    return _extract_value_from_citation_text(raw_text, volume_p)


def get_issue_number(article):
    issue_p = re.compile(r"\. \d+\((\d+)\)\.")
    raw_text = get_citation_text(article)
    return _extract_value_from_citation_text(raw_text, issue_p)

def get_keywords(article):
    # /html/body/div[2]/main/article/section[2]/div/div/div/div/p[4]/text()
    keywords_xpath = "string(//div[@id='article']/p[strong/text()='Keywords:']/text())"
    return article.xpath(keywords_xpath).strip()

def get_title(article) -> str:
    # Not all publication titles are on the same XPath.
    # This works for title-with-a-background-image-style titles used in
    # ITAA and MMB
    title_xpath1 = "//figcaption[@class='orbit-caption']/h3"

    # This works for no-background-image-style titles used in AHAC
    title_xpath2 = "//small/following-sibling::h3"

    try:
        title = article.xpath(title_xpath1)[0].text
    except IndexError:
        try:
            title = article.xpath(title_xpath2)[0].text
        # Sometimes we'll encounter Permission Denied (<h2>) or Server Error (<h4>)
        # messages instead of an article page. Since such headings aren't useful
        # titles and don't adhere to a consistent style, we'll just return a blank
        # string. Failing gracefully is usually preferable to crashing in this case.
        except IndexError:
            title = ""

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


def article_metadata_from_urls_to_tsv(urls: list, outfile: str, get_dois: bool=False) -> None:
    articles = get_etrees_from_urls(urls)
    md = get_article_metadata_from_etrees(articles, get_dois)
    out_md = [(u, *m) for u, m in zip(urls, md)]
    
    write_metadata_to_tsv(out_md, outfile)


def article_metadata_to_tsv(urls: list, articles: list, outfile: str, get_dois: bool=False) -> None:
    md = get_article_metadata_from_etrees(articles, get_dois)
    out_md = [(u, *m) for u, m in zip(urls, md)]
    
    write_metadata_to_tsv(out_md, outfile)


def write_metadata_to_tsv(out_md, outfile):
    with open(outfile, "w", encoding="utf-8") as fh:
        for row in out_md:
            row = [e if type(e) != list else ";".join(e) for e in row]
            line = "\t".join(row)
            fh.write(f"{line}\n")


def get_article_contributors_from_etrees(articles):
    return _etree_loop_get(articles, get_contributors)


def get_article_dois_from_etrees(articles):
    return _etree_loop_get(articles, get_doi)


def get_article_publication_years_from_etrees(articles):
    return _etree_loop_get(articles, get_publication_year)


def get_article_titles_from_etrees(articles):
    return _etree_loop_get(articles, get_title)


def get_article_volume_numbers_from_etrees(articles):
    return _etree_loop_get(articles, get_volume_number)


def get_article_issue_numbers_from_etrees(articles):
    return _etree_loop_get(articles, get_issue_number)


def get_article_titles_from_urls(urls: list) -> list:
    return _url_loop_get(urls, get_title)


def get_article_full_text_urls_from_etrees(articles):
    full_text_urls = []
    for article in articles:
        full_text_urls.append(get_full_text_url(article))

    return full_text_urls


def get_article_metadata_from_etrees(articles: list, get_dois=False) -> zip:
    titles = get_article_titles_from_etrees(articles)
    contributors = get_article_contributors_from_etrees(articles)
    dates = get_article_publication_years_from_etrees(articles)

    if get_dois:
        dois = get_article_dois_from_etrees(articles)
        return zip(dois, titles, contributors, dates)
    else:
        return zip(titles, contributors, dates)



def _etree_loop_get(trees: list, get_func) -> list:
    accumulator = []
    for tree in trees:
        accumulator.append(get_func(tree))

    return accumulator

def _url_loop_get(urls: list, get_func) -> list:
    trees = get_etrees_from_urls(urls)
    return _etree_loop_get(trees, get_func)


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
