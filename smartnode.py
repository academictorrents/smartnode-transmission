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

managed_torrents_file = "managed_torrents.csv"
tohave_torrents_file = "tohave_torrents.csv"
collections_folder = "collections"
collections_urls = "collections_urls.txt"

# loop over all csv files to sync
with open(collections_urls, "r") as urls:
    for url in urls:
        url = url.strip()
        if (url != ""):
            print(url)
            filedata = urllib.request.urlopen(url)  
            datatowrite = filedata.read()

            # detect more errors here

            os.makedirs(collections_folder, exist_ok=True)
            with open(collections_folder + "/" + os.path.basename(url), 'wb') as f:  
                f.write(datatowrite)

tohave_torrents = pd.DataFrame(columns = ['INFOHASH'])
tohave_torrents.set_index("INFOHASH", inplace=True)

for f in os.listdir(collections_folder):
    a = pd.read_csv(collections_folder + "/" + f)
    a.set_index("INFOHASH", inplace=True)
    a["COLLECTION"] = f
    tohave_torrents = tohave_torrents.append(a, sort=False)
    
# take union
tohave_torrents = tohave_torrents.drop_duplicates()
print("Total torrents from all collections: ", len(tohave_torrents))

if not os.path.isfile(managed_torrents_file):
    tohave_torrents.to_csv(managed_torrents_file)
    
managed_torrents = pd.read_csv(managed_torrents_file)
managed_torrents.set_index("INFOHASH", inplace=True)

toremove_torrents = set(managed_torrents.index) - set(tohave_torrents.index)



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
cookie_key = ""
if cookies != "":
    cookie_key = dict([k.split("=") for k in cookies.split(";")])


userannounce = None
def get_userannounce():
    global userannounce
    if cookie_key == "":
        userannounce = "https://academictorrents.com/announce.php"
    if userannounce is None:
        resp = requests.get(url="https://academictorrents.com/apiv2/userannounce", cookies=cookie_key)
        userannounce = resp.json()["userannounce"] # Check the JSON Response Content documentation below
    return userannounce


def fix_trackers():
    # check to remove or update trackers
    for torrentid in torrents:
        torrentobj = torrents[torrentid]
        
#         if torrentobj.hashString in toremove_torrents:
#             print("Something to remove", torrentobj.hashString, torrentid, torrentobj.name)
#             # do something to remove it
            
        #if torrentobj.hashString in tohave_torrents.index:
        #print(torrentobj.hashString, torrentid, torrentobj.name)
        torrentobj = client.get_torrent(torrentid)
        for index, tracker in enumerate(torrentobj.trackers):
            if ("academictorrents.com" in tracker["announce"]):
                if (tracker["announce"] != get_userannounce()):
                    print("Updating tracker at index",index, torrentobj.hashString, torrentid, torrentobj.name)
                    client.change_torrent(torrentid, trackerReplace=[index,get_userannounce()])
                    client.reannounce(torrentid)

#fix_trackers()

# add what we don't have
print("To download " + str(len(tohave_torrents.index)))
#print(tohave_torrents)
for index, torrent in tohave_torrents.iterrows():
    if torrent.name not in torrents_in_server:
        print("INFOHASH: " + torrent.name)
        print("SIZEBYTES: " + str(torrent["SIZEBYTES"]))
        free_space = client.free_space(download_path)
        print("Free space: ", free_space)
        if ((torrent["SIZEBYTES"] < 100000000000) and (free_space > torrent["SIZEBYTES"]*2)):
            url = "https://academictorrents.com/download/" + torrent.name + ".torrent"
            print(url)
            try:
                resp = requests.get(url=url, cookies=cookie_key).content                                    
                client.add_torrent(base64.b64encode(resp).decode('utf-8'))
                client.add_torrent(url, cookies=cookies)
                time.sleep(30) 
            except Exception as e: 
                print(e)
        else:
            print("Skipping due to size")



        
        

# filter tohave_torrents based on what we have with some sort of logic







