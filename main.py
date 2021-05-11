# coding=utf-8
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


def gyazoUpload(file_name, imagedata, content_type, title, url, desc, timestamp):
    """
    画像のバイナリと各種メタデータを指定してGyazoへのアップロードを実行するメソッド
    
    Args:
        file_name (str): 画像のファイル名
        imagedata (binary): 画像のバイナリ
        content_type (str): 画像の mime content type
        title (str): 画像を取得したウェブサイトのタイトル
        url (str): 画像を取得したウェブサイトのURL
        desc (str): Gyazo の Description 欄に記入されるメモ
        timestamp (int): 画像の最終変更日時
    """
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

    # Gyazoにアップロードするための multipart/form-data をつくる
    # filedata
    files = {'imagedata': (file_name, imagedata, content_type)}

    # metadata
    metadata = {
        'app': "twint-gyazo",
        'title': title,
        'url': url,
        'desc': desc
    }

    # formdata
    formdata = {
        'id': device_id,
        'scale': "1.0",
        'created_at': timestamp,
        'metadata': json.dumps(metadata)
    }

    gyazo_res = requests.post("https://upload.gyazo.com/upload.cgi", data=formdata, files=files)
    print(gyazo_res)
    print(gyazo_res.text)


def gyazoImage(image_url, screen_name, name, tweet, tweet_url, retweeted_by=None, index=0):
    """
    指定されたTwitterの画像をGyazoにアップロードするメソッド
    
    Args:
        image_url (str): Gyazo にアップロードしたいツイート内の画像
        screen_name (str): 画像をツイートした Twitter ユーザーの screen name
        name (str): 画像をツイートした Twitter ユーザーの名前
        tweet (str): ツイート本文
        tweet_url (str): ツイートの URL
        retweeted_by (str): 画像を RT した Twitter ユーザーの screen name
    """
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
    # 同じunix timestampだと困るのでindexごとに増やす
    timestamp += index

    # Twitterのタイトルを取得する
    """
    tweet_mobile_url = tweet_url.replace('twitter.com', 'mobile.twitter.com')
    print(tweet_mobile_url)
    html = requests.get(tweet_mobile_url).text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find('title')
    print(title.string)
    """
    title = f"{name}さんのツイート: \"{tweet}\" / Twitter"
    print(title)

    # Gyazoで管理するためにハッシュタグをきめる
    desc = ""
    tweet_hash = "#twitter_"+screen_name
    desc = desc+tweet_hash
    if retweeted_by != None:
        retweet_hash = "#twitter_rt_"+retweeted_by
        desc = desc+" "+retweet_hash
    # TODO: likeへの対応
    gyazoUpload(file_name, imagedata, content_type, title, tweet_url, desc, timestamp)



def gyazoTweet(screen_name, tweet):
    """
    指定されたTweetの画像をGyazoに保存するメソッド
    
    Args:
        tweet (tweet obj): twint.output.tweets_list で得られるTweet
    """
    # dictだったりそうじゃなかったりする（twint罰）
    if isinstance(tweet, dict):
        # 自分自身
        if screen_name == tweet['username']:
            for i, photo in enumerate(tweet['photos']):
                gyazoImage(photo, screen_name, tweet['name'], tweet['tweet'], tweet['link'], index=i)
        # RT
        else:
            for i, photo in enumerate(tweet['photos']):
                gyazoImage(photo, tweet['username'], tweet['name'], tweet['tweet'], tweet['link'], retweeted_by=screen_name, index=i)
    else:
        if screen_name == tweet.username:
            for i, photo in enumerate(tweet.photos):
                gyazoImage(photo, screen_name, tweet.name, tweet.tweet, tweet.link, index=i)
        else:
            for i, photo in enumerate(tweet.photos):
                gyazoImage(photo, tweet.username, tweet.name, tweet.tweet, tweet.link, retweeted_by=screen_name, index=i)


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
    c.Username = screen_name
    c.Store_object = True
    #c.Store_json = True
    # 標準出力へログ出力するか否か
    c.Hide_output = True
    # 標準出力へのログ出力のフォーマット
    #c.Format = 'twint account: - {username} - {id}'
    # retweetを含めるか
    c.Retweets = include_retweets
    # 画像つきツイートのみ取得する
    c.Images = True
    # 何件取得するか
    c.Limit = limit
    # Searchでタイムライン取得を実行する
    twint.run.Search(c)
    tweets = twint.output.tweets_list
    print("twintGetUserTweets: "+str(len(tweets)))
    return tweets


def gyazoTweetedPhotos(screen_name):
    '''
    特定のTwitterユーザーがツイートした全画像をGyazoに保存するメソッド
    
    Args:
        screen_name (str): 画像を取得したいユーザーのscreen_name
    '''
    tweets = twintGetUserTweets(screen_name, include_retweets=True)
    # twintが狂ってて取得ツイートが空になることが頻繁にあるので、その場合はリトライする
    if len(tweets) == 0:
        time.sleep(5)
        gyazoTweetedPhotos(screen_name)
    else:
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
    if targetMethod != None:
        if targetMethod == "gyazo":
            gyazoTweetedPhotos(optionalArg)
