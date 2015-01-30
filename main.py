# imports
import requests
import os
import sys
from bs4 import BeautifulSoup
from datetime import date

# global variables
BASE_URL = "http://www.mangahere.co/manga/kangoku_gakuen/" # default base url
DOWNLOAD_BASE_DIR = os.getcwd() + "/prison-school" # default base directory


# methods
def get_chapter_list(soup):
    list_items = []
    for div in soup.find_all('div'):
        if div.has_attr('class') and div['class'][0] == u'detail_list':
            list_items.append(div.ul)

    return list_items

def get_chapter_urls(list_items):
    """
    returns:
        a list of list[name, chapter number, date, url]
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
            left_span = None
            right_span = None
            for span in li.find_all('span'):
                if span.has_attr('class') and span['class'][0] == u'right':
                    # print span.text,
                    right_span = span

                if span.has_attr('class') and span['class'][0] == u'left':
                    # print span.a['href']
                    left_span = span

            date = right_span.text
            url = left_span.a['href']
            chap_no = left_span.a.text.strip()
            name = left_span.get_text()[left_span.get_text().rfind('\n'):].strip()
            
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
    # print image_url
    # print next_page_url

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
    if len(name) > 0:
        name = '-' + name
    name = name.replace(',','')
    name = name.replace('.','')
    name = name.replace(" ","-")
    name = str(chap_no.split()[-1].zfill(3)) + name
    path = DOWNLOAD_BASE_DIR + "/" + name
    if not os.path.exists(path):
        os.makedirs(path)
        _download_chapter(chap_url, path)
    elif not os.path.exists(path + "/.complete"):
        _download_chapter(chap_url, path)

    print "DOWNLOADED! " + path + "\n\n"


today_string = date.today().strftime("%B")[:3] + date.today().strftime(" %d, %Y")

if __name__ == "__main__":
    if len(sys.argv) == 3:
        BASE_URL = sys.argv[1]
        if BASE_URL[-1] != '/':
            BASE_URL += '/'
        DOWNLOAD_BASE_DIR = os.getcwd() + "/" + sys.argv[2]

        if DOWNLOAD_BASE_DIR[-1] == '/':
            DOWNLOAD_BASE_DIR = DOWNLOAD_BASE_DIR[:-1]

        print "Downloading with custom values: ", BASE_URL, DOWNLOAD_BASE_DIR, "\n";
    elif len(sys.argv) == 1:
        print "Downloading with default values...\n"
    else:
        print "Correct usage: python main.py <manga base url> <folder name in the current dir to download>\n"
        sys.exit(1)

    if not os.path.exists(DOWNLOAD_BASE_DIR):
        os.makedirs(DOWNLOAD_BASE_DIR)

    soup = BeautifulSoup(requests.get(BASE_URL).text)
    urls = get_chapter_urls(get_chapter_list(soup))
    for url in urls:
        download_chapter(url[0], url[1], url[-1])
