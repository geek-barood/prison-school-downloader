# imports
import requests
import os
import sys
import bs4
from bs4 import BeautifulSoup, SoupStrainer
from datetime import date
import timeit
import Queue, threading

# global variables
BASE_URL = "http://www.mangahere.co/manga/kangoku_gakuen/" # default base url
DOWNLOAD_BASE_DIR = os.path.join(os.getcwd(),"prison-school") # default base directory
DOWNLOAD_MODE = 0
task_queue = None

# Thread worker class
class ConsumerThread(threading.Thread):
    """ This thread runs in the background when a chapter is started.
        The task queue contains a tuple (image_url, dump_path)

        It checks the Task queue if there are any task left to do(having a
        timeout seconds till it holds the queue to check, and if it finds one
        it runs the image_download() method as a new thread
    """
    def __init__(self, _queue):
        super(ConsumerThread, self).__init__()
        self._queue = _queue
        self.stoprequest = threading.Event()

    def run(self):
        while not self.stoprequest.isSet():
            try:
                image_url, dump_path = self._queue.get(True, 0.05)
                threading.Thread(target=download_image, args=(image_url,dump_path)).start()
            except Queue.Empty:
                continue

# methods
def get_chapter_urls(soup):
    """
    returns:
        a list of list[name, chapter number, url]
    """
    urls = []
    spans = soup.find_all('span', class_=u'left')
    for span in spans:
        if type(span.a) is bs4.element.Tag:
            urls.append([span.get_text()[span.get_text().rfind('\n'):].strip(),\
                    span.a.text.strip(),\
                    span.a['href']])

    return urls

def crawl_for_images(queue, url, dad, directory_loc):
    curr_page = requests.get(url).text
    viewer = SoupStrainer(id="viewer")
    curr_soup = BeautifulSoup(curr_page, parse_only=viewer)

    image_url = curr_soup.find(id="image")['src']
    image_url = image_url[:image_url.find('?')].strip()
    next_page_url = curr_soup.a["href"].strip()

    filename = image_url[image_url.rfind("/")+1:]
    dump_path = os.path.join(directory_loc, filename)
    if not os.path.isfile(dump_path):
        # add_task_to_queue(queue, image_url, dump_path)
        threading.Thread(target=add_task_to_queue, args=(queue, image_url,dump_path)).start()

    if url == next_page_url or next_page_url[:4] != "http":
        return

    crawl_for_images(queue, next_page_url, url, directory_loc)


def add_task_to_queue(queue, image_url, dump_path):
    queue.put((image_url, dump_path))

def crawl_chapter(queue, chap_url, directory_loc):
    if DOWNLOAD_MODE == 0:
        print "getting image urls for chapter: ", chap_url
    crawl_for_images(queue, chap_url, None, directory_loc)

def download_image(image_url, dump_path):
    """ This method adds the task to the queue
    """
    # refer to this link for details:
    # https://www.codementor.io/tips/3443978201/how-to-download-image-using-requests-in-python

    r = requests.get(image_url, stream=True)
    print "downloading " + image_url + " to: " + dump_path
    if r.status_code == 200:
        with open(dump_path, 'wb') as f:
            # default is 128 byte chunk size which takes too much of CPU
            for chunk in r.iter_content(1024):
                f.write(chunk)


def _download_chapter(queue, chap_url, file_location):
    crawl_chapter(queue, chap_url, file_location)

def download_chapter(queue, name, chap_no, chap_url):
    if len(name) > 0:
        name = '-' + name
    name = name.replace(',','').replace('.','').replace(' ','-')
    name = str(chap_no.split()[-1].zfill(3)) + name
    path = os.path.join(DOWNLOAD_BASE_DIR, name)
    if not os.path.exists(path):
        os.makedirs(path)
        _download_chapter(queue, chap_url, path)
    elif not os.path.exists(path + "/.complete"):
        _download_chapter(queue, chap_url, path)

    print "DOWNLOADED! " + path + "\n\n"


today_string = date.today().strftime("%B")[:3] + date.today().strftime(" %d, %Y")

if __name__ == "__main__":
    if len(sys.argv) == 3 or len(sys.argv) == 4:
        if len(sys.argv) == 4:
            if sys.argv[3] == '-m':
                DOWNLOAD_MODE = 1
        BASE_URL = sys.argv[1]
        if BASE_URL[-1] != '/':
            BASE_URL += '/'

        DOWNLOAD_BASE_DIR = os.path.join(os.getcwd(), sys.argv[2])
        print "Downloading with custom values " + "multi mode" if DOWNLOAD_MODE==1 else "normal mode",": ", BASE_URL, DOWNLOAD_BASE_DIR, "\n"
    elif len(sys.argv) == 1:
        print "Downloading with default values...\n"
    else:
        print "Correct usage: python main.py <manga base url> <folder name in \
        the current dir to download> [OPTION]\n OPTION\n---------\n m: multi \
        chapter mode\n s: single chapter mode(default)\n"
        sys.exit(1)

    if not os.path.exists(DOWNLOAD_BASE_DIR):
        os.makedirs(DOWNLOAD_BASE_DIR)

    start = timeit.default_timer()
    page = requests.get(BASE_URL).text
    end = timeit.default_timer()
    if __debug__:
        print "time take to request the url: ", end - start

    start = timeit.default_timer()
    divs = SoupStrainer('div')
    soup = BeautifulSoup(page, parse_only=divs)
    end = timeit.default_timer()
    if __debug__:
        print "time taken to build the soup object: ", end - start

    start = timeit.default_timer()
    urls = get_chapter_urls(soup)
    end = timeit.default_timer()
    if __debug__:
        print "time taken to get_chapter_urls(soup): ", end - start

    task_queue = Queue.Queue()
    ConsumerThread(task_queue).start()
    for url in urls:
        if DOWNLOAD_MODE == 1:
            threading.Thread(target=download_chapter, args=(task_queue,url[0],url[1],url[-1])).start()
        else:
            download_chapter(task_queue, url[0], url[1], url[-1])


