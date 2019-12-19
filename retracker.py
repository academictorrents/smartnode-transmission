import sys
import datetime
import sqlite3
import time
import xml.etree.ElementTree as ET
import lib.transmissionrpc
import getpass
import urllib
import re, os
import pandas as pd
import base64
import requests


import configparser
config = configparser.RawConfigParser()
config.read('smartnode.properties')

client = lib.transmissionrpc.Client(address = config.get("Transmission","address"), 
                                port=int(config.get("Transmission","port")),
                                user = config.get("Transmission","user"), 
                                password = config.get("Transmission","password"))



## TODO finish transmission interface part


torrents = client.list()
torrents_in_server = set([torrents[t].hashString for t in torrents])


download_path = client.get_session().download_dir
cookies = config.get("AcademicTorrents","api_key")
cookie_key = dict([k.split("=") for k in cookies.split(";")])


userannounce = None
def get_userannounce():
    global userannounce
    if userannounce is None:
        resp = requests.get(url="https://academictorrents.com/apiv2/userannounce", cookies=cookie_key)
        userannounce = resp.json()["userannounce"] # Check the JSON Response Content documentation below
    return userannounce


def fix_trackers():
    # check to remove or update trackers
    for torrentid in torrents:
        torrentobj = torrents[torrentid]
        torrentobj = client.get_torrent(torrentid)
        for index, tracker in enumerate(torrentobj.trackers):
            if ("academictorrents.com" in tracker["announce"]):
                if (tracker["announce"] != get_userannounce()):
                    print("Updating tracker at index",index, torrentobj.hashString, torrentid, torrentobj.name)
                    client.change_torrent(torrentid, trackerReplace=[index,get_userannounce()])
                    client.reannounce(torrentid)

fix_trackers()







