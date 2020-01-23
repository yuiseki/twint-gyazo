import os
import sys
import json
import platform

import time
import datetime
import base64

from urllib.parse import urlparse
from dateutil.parser import parse

import twint
import requests
from bs4 import BeautifulSoup

def gyazoImage(image_url, screen_name, tweet_url, retweeted_by=None):
    # 画像を取得する
    parsed_url = urlparse(image_url)
    file_name = os.path.basename(parsed_url.path)
    response = requests.get(image_url)
    imagedata = response.content

    # ファイルタイプを取得する
    # 謎だけどたまにこういうやつがいるので無視
    if not 'content-type' in response.headers:
        return
    content_type = response.headers['content-type']
    print(content_type)

    # 変更時刻を取得する
    # 謎だけどたまにこういうやつがいるので無視
    if not 'last-modified' in response.headers:
        return
    last_modified = response.headers['last-modified']
    print(last_modified)
    # unixtimeに変換する
    timestamp = int(parse(last_modified).timestamp())

    # Twitterのタイトルを取得する
    html = requests.get(tweet_url).text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string

    # Device IDを取得する
    appdata_path = None
    appdata_filename = None
    if 'Darwin' in platform.system():
        appdata_path = os.path.expanduser('~/Library/Gyazo/')
        appdata_filename = 'id'
    elif 'Windows' in platform.system() or 'CYGWIN' in platform.system():
        appdata_path = os.getenv('APPDATA') + '\\Gyazo\\'
        appdata_filename = 'id.txt'
    elif 'Linux' in platform.system():
        appdata_path = os.path.expanduser('~/')
        appdata_filename = '.gyazo.id'

    with open(('%s%s' % (appdata_path, appdata_filename)), 'r') as device_id_file:
        device_id = device_id_file.read()

    # Gyazoにアップロードするための formdata をつくる
    # metadata
    desc = ""
    tweet_hash = "#twitter_"+screen_name
    desc = desc+tweet_hash
    if retweeted_by is not None:
        retweet_hash = "#twitter_rt_"+retweeted_by
        desc = desc+" "+retweet_hash
    metadata = {
        'app': "twint-gyazo",
        'title': title,
        'url': tweet_url,
        'desc': desc
    }
    # formdata
    formdata = {
        'id': device_id,
        'scale': "1.0",
        'created_at': timestamp,
        'metadata': json.dumps(metadata)
    }
    # filedata
    files = {'imagedata': (file_name, imagedata, content_type)}
    gyazo_res = requests.post("https://upload.gyazo.com/upload.cgi", data=formdata, files=files)
    print(gyazo_res)
    print(gyazo_res.text)


def gyazoTweet(screen_name, tweet):
    """
    指定されたTweetの画像をGyazoに保存するメソッド
     
    Args:
        tweet (tweet obj): twint.output.tweets_list で得られるTweet
    """
    # dictだったりそうじゃなかったりする（twint罰）
    if isinstance(tweet, dict):
        if screen_name == tweet['username']:
            for photo in tweet['photos']:
                gyazoImage(photo, screen_name, tweet['link'])
        else:
            for photo in tweet['photos']:
                gyazoImage(photo, tweet['username'], tweet['link'], retweeted_by=screen_name)
    else:
        if screen_name == tweet.username:
            for photo in tweet.photos:
                gyazoImage(photo, screen_name, tweet.link)
        else:
            for photo in tweet.photos:
                gyazoImage(photo, tweet.username, tweet.link, retweeted_by=screen_name)




def twintGetUserTweets(screen_name, limit=4000, include_retweets=True):
    '''
    特定のユーザーのTwitterタイムラインを取得するメソッド
     
    Args:
        screen_name (str): 収集したいユーザーの screen_name
        limit (int): 取得件数（Twitterの仕様上4000件くらいが限界）
        include_retweets (bool): リツイートを含めるか否か
     
    Returns:
        tweets (array)
    '''
    print("twintGetUserTweets: "+screen_name)
    twint.output.users_list = []
    twint.output.tweets_list = []
    c = twint.Config()
    c.Store_object = True
    c.Store_json = True
    # 標準出力へログ出力するか否か
    c.Hide_output = False
    # 標準出力へのログ出力のフォーマット
    c.Format = 'twint account: - {username} - {id}'
    c.Username = screen_name
    # retweetを含めるか
    c.Retweets = include_retweets
    # 何件取得するか
    c.Limit = limit
    # Profileでタイムライン取得を実行する
    twint.run.Profile(c)
    tweets = twint.output.tweets_list
    return tweets


def gyazoTweetedPhotos(screen_name):
    '''
    特定のTwitterユーザーがツイートした全画像をGyazoに保存するメソッド
     
    Args:
        screen_name (str): 画像を取得したいユーザーのscreen_name
    '''
    tweets = twintGetUserTweets(screen_name, include_retweets=True)
    for tweet in tweets:
        gyazoTweet(screen_name, tweet)



def printUsage():
    print("""
python main.py gyazo screen_name
    gyazoTweetedPhotos(screen_name)
    screen_name のユーザーがツイートした画像を全部Gyazoに保存するコマンド
""")


targetMethod = None
optionalArg = None
if __name__ == "__main__":
    if (len(sys.argv) == 1):
        printUsage()
    if (len(sys.argv) >= 2):
        targetMethod = sys.argv[1]
    if (len(sys.argv) >= 3):
        optionalArg = sys.argv[2]
    if targetMethod is not None:
        if targetMethod == "gyazo":
            gyazoTweetedPhotos(optionalArg)
