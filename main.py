# imports
import requests
import os
from bs4 import BeautifulSoup
from datetime import date

# global variables
BASE_URL = "http://www.mangahere.co/manga/kangoku_gakuen/"
DOWNLOAD_BASE_DIR = os.getcwd() + "/prison-school"
soup = BeautifulSoup(requests.get(BASE_URL).text)
today_string = date.today().strftime("%B")[:3] + date.today().strftime(" %d, %Y")


# methods
def get_chapter_list():
    list_items = []
    for div in soup.find_all('div'):
        if div.has_attr('class') and div['class'][0] == u'detail_list':
            list_items.append(div.ul)

    return list_items

def get_chapter_urls(list_items):
    """
    returns:
        a list of list[name, date, url]
    params:
        list_items: list of chapters as div.ul
    """

    tag_type = type(BeautifulSoup("<a></a>").a)
    navigable_string_type = type(BeautifulSoup("<a>s</a>").string)
    chapter_urls = []

    for li in list_items[0]:
        url = None
        date = None
        name = None
        chap_no = None
        if type(li) == tag_type:
            for span in li.find_all('span'):
                if span.has_attr('class') and span['class'][0] == u'right':
                    # print span.text,
                    date = span.text
                if span.has_attr('class') and span['class'][0] == u'left':
                    # print span.a['href']
                    url = span.a['href']
                    chap_no = span.a.text.strip()

                if len(span.contents) > 2:
                    name = span.contents[-1].strip()

                if url is not None and date is not None:
                    if date.lower() == "today":
                        date = today_string
                    chapter_urls.append([name, chap_no, date, url])

    return chapter_urls

def crawl_for_images(url, dad, url_list):
    curr_page = requests.get(url).text
    curr_soup = BeautifulSoup(curr_page)

    section = curr_soup.find(id="viewer")
    image_url = section.find(id="image")['src']
    image_url = image_url[:image_url.find('?')].strip()
    next_page_url = section.a["href"].strip()
    print image_url
    print next_page_url

    url_list.append(image_url)
    if url == next_page_url or next_page_url[:4] != "http":
        return

    crawl_for_images(next_page_url, url, url_list)

def get_chapter_image_urls(chap_url):
    urls = []
    crawl_for_images(chap_url, None, urls)
    return urls

def _download_chapter(chap_url, file_location):
    # refer to this link for details:
    # https://www.codementor.io/tips/3443978201/how-to-download-image-using-requests-in-python

    image_urls = get_chapter_image_urls(chap_url)
    for image_url in image_urls:
        filename = image_url[image_url.rfind("/")+1:]
        print "downloading " + image_url + " to: " + file_location + "/" + filename
        r = requests.get(image_url, stream=True)
        if r.status_code == 200:
            with open(file_location + "/" + filename, 'wb') as f:
                # default is 128 byte chunk size which takes too much of CPU
                for chunk in r.iter_content(1024):
                    f.write(chunk)

    with open(file_location + "/.complete", 'w') as f2:
        f2.write(str(len(image_urls)))


def download_chapter(name, chap_no, chap_url):
    name = name.replace(" ","-")
    name = str(chap_no.split()[-1].zfill(3)) + "-" + name
    path = DOWNLOAD_BASE_DIR + "/" + name
    if not os.path.exists(path):
        os.makedirs(path)
        _download_chapter(chap_url, path)
    elif not os.path.exists(path + "/.complete"):
        _download_chapter(chap_url, path)

    print "done downloading " + path


if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_BASE_DIR):
        os.makedirs(DOWNLOAD_BASE_DIR)

    urls = get_chapter_urls(get_chapter_list())
    for url in urls:
        download_chapter(url[0], url[1], url[-1])
