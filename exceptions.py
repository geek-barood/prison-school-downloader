__author__ = 'Aniruddha Hazra'


class DownloadError(Exception):
    def __init__(self, msg=''):
        self.message = msg

    def __init__(self, url, path, msg):
        self.url = url
        self.path = path
        self.msg = msg


class MaxRetriesError(DownloadError):
    def __init__(self, url, path):
        self.msg = 'Max retries exceeded'
        super(url, path, self.msg)