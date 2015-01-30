# Prison School Downloader
-----------------------------
An "intelligent" manga downloader.
It can download mangas from [mangahere](http://www.mangahere.co)
and dump them chapter by chapter (starting from the most recent)
to your specified location.

### Usage
-----------------------------
#### Installing
1. Clone or download the repository.
2. If you have requests and beautifulsoup4 installed then you are good to go.
3. Otherwise
  1. install virtualenv from the terminal: `$ sudo easy_install virtualenv`
  2. go to the cloned directory root and type in terminal: `$ source bin/activate`

#### Running
```
$ python main.py <root url of the manga in mangahere site> <name of the directory>
```
eg. 
```
python main.py http://www.mangahere.co/manga/kangoku_gakuen/ prison-school/
```
It will download all the chapters starting from the most recent one and dump them in `./prison-school`

### Contribution
--------------------------------
If you find any bugs or need a feature feel free to report or ask.

If you want to add some feature you are most welcome to do so.
:)
