#TODO fix issue: every exception kills/closes the thread which got the
#               exception
#TODO add failed download retry feature
#TODO add Logging

# imports
import requests
import os
import sys
import bs4
from bs4 import BeautifulSoup, SoupStrainer
from datetime import date
import timeit
import Queue, threading
import re, unicodedata

fail_list = [] # stores the list of tuples (url,download path) which failed
               # to download
# Thread worker class
class ConsumerThread(threading.Thread):
    """ This thread runs in the background when a the program runs.
        The task queue contains a tuple (image_url, dump_path)

        It checks the Task queue if there are any task left to do(having a
        timeout seconds till it holds the queue to check, and if it finds one
        it runs the image_download() method as a new thread
    """
    def __init__(self, _queue, max_retries):
        super(ConsumerThread, self).__init__()
        self._queue = _queue
        self.max_retries = max_retries
        self.stoprequest = threading.Event()

    def join(self, timeout=None):
        self.stoprequest.set()
        super(ConsumerThread, self).join(timeout)

    def run(self):
        while not self.stoprequest.isSet():
            try:
                image_url, dump_path, attempt = self._queue.get(True, 0.05)
                MangaDownloader.download_image(self._queue, image_url, dump_path,\
                            attempt, self.max_retries)
            except Queue.Empty:
                continue

class MangaDownloader:
    def __init__(self, q, max_retries):
        self._queue = q
        self.directory = None
        self.MAX_RETRIES =  max_retries
        self.today_string = date.today().strftime("%B")[:3]\
                            + date.today().strftime(" %d, %Y")

    def set_output_dir(self, path):
        self.directory = path

    def get_chapter_urls(self, soup):
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

    def crawl_for_images(self, url, dad, chap_path):
        try:
            curr_page = requests.get(url).text
        except (requests.exceptions.ConnectionError,\
                requests.exceptions.Timeout) as e:
            print "Error crawling for image:", e.args[0].reason
            return

        viewer = SoupStrainer(id="viewer")
        curr_soup = BeautifulSoup(curr_page, parse_only=viewer)

        image_url = curr_soup.find(id="image")['src']
        image_url = image_url[:image_url.find('?')].strip()
        next_page_url = curr_soup.a["href"].strip()

        filename = image_url[image_url.rfind("/")+1:]
        dump_path = os.path.join(chap_path, filename)

        if not os.path.isfile(dump_path):
            # add task to the queue
            self.add_task_to_queue(image_url,dump_path)
        else:
            print image_url, "is already present"

        if url == next_page_url or next_page_url[:4] != "http":
            return

        self.crawl_for_images(next_page_url, url, chap_path)


    def add_task_to_queue(self, image_url, dump_path):
        self._queue.put((image_url, dump_path, 1))

    def crawl_chapter(self, chap_url, chap_path):
        self.crawl_for_images(chap_url, None, chap_path)

    @staticmethod
    def download_image(queue, image_url, dump_path, attempt, max_retries):
        """
        This method adds the task to the task queue.
        If any error occurs it adds to the task queue again if number of
        attempts is not exceeding max number of retries.

        It also adds the failed files to the failed list so that it will
        create a file inside the current chapter which lists which files failed.
        (Yet to implement the above feature)
        """
        try:
            r = requests.get(image_url, stream=True, timeout=3)
            if r.status_code == 200:
                with open(dump_path, 'wb') as f:
                    # default small chunk size takes too much of CPU
                    for chunk in r.iter_content(chunk_size=1024):
                        f.write(chunk)

                print "downloaded", image_url
            elif r.status_code == 404:
                print "Image not found!"
            else:
                print "Error downloading image", image_url

        except (requests.exceptions.Timeout,\
                requests.exceptions.ConnectionError):
            if attempt > max_retries:
                print "downloading", image_url, "failed"
                fail_list.append((image_url, dump_path))
            else:
                print "retrying("+str(attempt)+")", image_url + "..."
                queue.put((image_url, dump_path, attempt+1))


    def _download_chapter(self, chap_url, chap_path):
        self.crawl_chapter(chap_url, chap_path)

    @staticmethod
    def slugify(value):
        """
        Converts to ASCII. Converts spaces to hyphens. Removes characters that
        aren't alphanumerics, underscores, or hyphens. Converts to lowercase.
        Also strips leading and trailing whitespace.
        """
        value = unicode(value)
        value = unicodedata.normalize('NFKD', value).encode('ascii','ignore').decode('ascii')
        value = re.sub('[^\w\s-]', '', value).strip().lower()
        return re.sub('[-\s]+','-',value)

    def download_chapter(self, name, chap_no, chap_url):
        if len(name) > 0:
            name = self.slugify(name)
            name = '-' + name

        name = str(chap_no.split()[-1].zfill(4)) + name
        chap_path = os.path.join(self.directory, name)
        if not os.path.exists(chap_path):
            os.makedirs(chap_path)
            self._download_chapter(chap_url, chap_path)
        elif not os.path.exists(chap_path + "/.complete"):
            self._download_chapter(chap_url, chap_path)



def main():
    if len(sys.argv) == 3:
        BASE_URL = sys.argv[1]
        if BASE_URL[-1] != '/':
            BASE_URL += '/'

        DOWNLOAD_BASE_DIR = os.path.join(os.getcwd(), sys.argv[2])
        print "Downloading with custom values ", BASE_URL, DOWNLOAD_BASE_DIR, "\n"
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
    try:
        page = requests.get(BASE_URL).text
    except (requests.exceptions.Timeout,\
            requests.exceptions.ConnectionError) as e:
        print "Error getting base url:", e.args[0].reason
        exit(0)

    end = timeit.default_timer()
    if __debug__:
        print "time take to request the url: ", end - start

    start = timeit.default_timer()
    divs = SoupStrainer('div')
    soup = BeautifulSoup(page, parse_only=divs)
    end = timeit.default_timer()
    if __debug__:
        print "time taken to build the soup object: ", end - start


    task_queue = Queue.Queue()
    manga_downloader = MangaDownloader(task_queue, max_retries=4)
    start = timeit.default_timer()
    urls = manga_downloader.get_chapter_urls(soup)
    end = timeit.default_timer()
    if __debug__:
        print "time taken to get_chapter_urls(soup): ", end - start

    thread_pool = [ConsumerThread(task_queue,\
            manga_downloader.MAX_RETRIES) for i in xrange(4)]
    for consumer in thread_pool:
        consumer.start()

    for url in urls:
        try:
            manga_downloader.set_output_dir(DOWNLOAD_BASE_DIR)
            manga_downloader.download_chapter(url[0], url[1], url[-1])
        except KeyboardInterrupt:
            print "\nKeyboard Interrupt received, closing threads..."
            break

    for consumer in thread_pool:
        consumer.join()
    print "All threads closed\n"
    print len(fail_list), "files failed!!"
    for fail in fail_list:
        print fail[0], fail[1]


if __name__ == '__main__':
    main()
