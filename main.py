# TODO fix issue: every exception kills/closes the thread which got the exception
# TODO add failed download retry feature
# TODO add Logging

import requests
import os
import sys
from bs4 import BeautifulSoup, SoupStrainer
from downloader import Downloader
import exceptions
import timeit
import Queue
import threading

_default_download_base_dir = os.path.join(os.getcwd(), 'prison-school')
_default_download_base_url = 'http://www.mangahere.co/manga/kangoku_gakuen/'


class ConsumerThread(threading.Thread):
    """ This thread runs in the background when a the program runs.
        The task queue contains a tuple (image_url, dump_path)

        It checks the Task queue if there are any task left to do(having a
        timeout seconds till it holds the queue to check, and if it finds one
        it runs the image_download() method as a new thread
    """
    def __init__(self, _id, _queue, downloader, max_retries):
        super(ConsumerThread, self).__init__(name=str(_id)+'-worker')
        self._id = _id
        self._queue = _queue
        self.max_retries = max_retries
        self.stoprequest = threading.Event()
        self.downloader = downloader

    def join(self, timeout=None):
        self.stoprequest.set()
        super(ConsumerThread, self).join(timeout)

    def run(self):
        while not self.stoprequest.isSet():
            try:
                image_url, dump_path, attempt = self._queue.get(True, 0.05)
            except Queue.Empty:
                continue
            try:
                Downloader.download_image(self._queue, image_url, dump_path, attempt+1, self.max_retries)
            except exceptions.DownloadError as e:
                print e.msg
                self.downloader.fail_list.append((e.url, e.path))


def main():
    download_base_dir = _default_download_base_dir
    base_url = _default_download_base_url

    if len(sys.argv) == 3:
        base_url = sys.argv[1]
        if base_url[-1] != '/':
            base_url += '/'

        download_base_dir = os.path.join(os.getcwd(), sys.argv[2])
        print 'Downloading with custom values ', base_url, download_base_dir, '\n'
    elif len(sys.argv) == 1:
        print 'Downloading with default values...\n'
    else:
        print 'Correct usage: python main.py <manga base url> <folder name in \
        the current dir to download> [OPTION]\n OPTION\n---------\n m: multi \
        chapter mode\n s: single chapter mode(default)\n'
        sys.exit(1)

    if not os.path.exists(download_base_dir):
        os.makedirs(download_base_dir)

    start = timeit.default_timer()
    try:
        page_resp = requests.get(base_url)
        # hack to check whether the url is from mangahere or not
        if str(page_resp.headers['set-cookie']).rfind('mangahere.co') != -1:
            if page_resp.status_code == 200:
                page = page_resp.text
            else:
                print 'Failed! Status code: ' + page_resp.status_code
                return
        else:
            print 'Error getting base url'
            return
    except (requests.exceptions.Timeout,
            requests.exceptions.ConnectionError) as e:
        print 'Error getting base url:', e.args[0].reason
        exit(0)

    end = timeit.default_timer()
    if __debug__:
        print 'time take to request the url: ', end - start

    start = timeit.default_timer()
    divs = SoupStrainer('div')
    soup = BeautifulSoup(page, parse_only=divs)
    end = timeit.default_timer()
    if __debug__:
        print 'time taken to build the soup object: ', end - start

    task_queue = Queue.Queue()
    manga_downloader = Downloader(task_queue, max_retries=4)
    start = timeit.default_timer()
    urls = manga_downloader.get_chapter_urls(soup)
    end = timeit.default_timer()
    if __debug__:
        print 'time taken to get_chapter_urls(soup): ', end - start

    thread_pool = [ConsumerThread(t_id, task_queue, manga_downloader,
                                  manga_downloader.MAX_RETRIES) for t_id in xrange(4)]
    for consumer in thread_pool:
        consumer.start()

    for url in urls:
        try:
            manga_downloader.set_output_dir(download_base_dir)
            manga_downloader.download_chapter(url[0], url[1], url[-1])
        except KeyboardInterrupt:
            print '\nKeyboard Interrupt received, closing threads...'
            break

    for consumer in thread_pool:
        consumer.join()
    print 'All threads closed\n'
    print len(manga_downloader.failures), 'files failed!!'
    for fail in manga_downloader.failures:
        print fail[0], fail[1]


if __name__ == '__main__':
    main()
