__author__ = 'Aniruddha Hazra'

import requests
import exceptions
import os
import re
import bs4
from bs4 import BeautifulSoup, SoupStrainer
from datetime import date
import unicodedata


class Downloader:

    def __init__(self, q, max_retries):
        self._queue = q
        self.directory = None
        self.failures = []  # stores the list of tuples (url,download path) which failed to download
        self.MAX_RETRIES = max_retries
        self.today_string = '{0}{1}'.format(date.today().strftime('%B')[:3], date.today().strftime(' %d, %Y'))

    def set_output_dir(self, path):
        self.directory = path

    def crawl_for_images(self, url, dad, chap_path):
        try:
            curr_page_resp = requests.get(url)
            if curr_page_resp.status_code == 200:
                curr_page = curr_page_resp.text
            else:
                print 'Page not found!'
                return
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print 'Error crawling for image'
            return

        viewer = SoupStrainer(id='viewer')
        curr_soup = BeautifulSoup(curr_page, parse_only=viewer)

        image_url = curr_soup.find(id='image')['src']
        image_url = image_url[:image_url.find('?')].strip()
        next_page_url = curr_soup.a['href'].strip()

        filename = image_url[image_url.rfind('/')+1:]
        dump_path = os.path.join(chap_path, filename)

        if not os.path.isfile(dump_path):
            # add task to the queue
            self.add_task_to_queue(image_url, dump_path)
        else:
            print image_url, 'is already present'

        if url == next_page_url or next_page_url[:4] != 'http':
            return

        self.crawl_for_images(next_page_url, url, chap_path)

    def add_task_to_queue(self, image_url, dump_path):
        self._queue.put((image_url, dump_path, 0))

    def crawl_chapter(self, chap_url, chap_path):
        self.crawl_for_images(chap_url, None, chap_path)

    def _download_chapter(self, chap_url, chap_path):
        self.crawl_chapter(chap_url, chap_path)

    def download_chapter(self, name, chap_no, chap_url):
        if len(name) > 0:
            name = self.slugify(name)
            name = '-' + name

        name = str(chap_no.split()[-1].zfill(4)) + name
        chap_path = os.path.join(self.directory, name)
        if not os.path.exists(chap_path):
            os.makedirs(chap_path)
            self._download_chapter(chap_url, chap_path)
        elif not os.path.exists(chap_path + '/.complete'):
            self._download_chapter(chap_url, chap_path)

    @staticmethod
    def get_chapter_urls(soup):
        """
        returns:
            a list of list[name, chapter number, url]
        """
        urls = []
        spans = soup.find_all('span', class_=u'left')
        for span in spans:
            if type(span.a) is bs4.element.Tag:
                urls.append([span.get_text()[span.get_text().rfind('\n'):].strip(),
                             span.a.text.strip(), span.a['href']])

        return urls

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

                print 'downloaded', image_url
            elif r.status_code == 404:
                print 'Image not found!'
            else:
                print 'Error downloading image', image_url

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt > max_retries:
                raise exceptions.MaxRetriesError(image_url, dump_path)
            else:
                print 'retrying('+str(attempt)+')', image_url + '...'
                queue.put((image_url, dump_path, attempt))

    @staticmethod
    def slugify(value):
        """
        Converts to ASCII. Converts spaces to hyphens. Removes characters that
        aren't alphanumerics, underscores, or hyphens. Converts to lowercase.
        Also strips leading and trailing whitespace.
        """
        value = unicode(value)
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub('[^\w\s-]', '', value).strip().lower()
        return re.sub('[-\s]+', '-', value)

