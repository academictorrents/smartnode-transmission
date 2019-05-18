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
    managed_torrents.to_csv(managed_torrents_file)
    
managed_torrents = pd.read_csv(managed_torrents_file)
managed_torrents.set_index("INFOHASH", inplace=True)




tc = lib.transmissionrpc.Client(address = "aa", 
                                port="9091",
                                user = "aaa", 
                                password = "aaa")

## TODO finish transmission interface part


# use the different between tohave_torrents and managed_torrents to remove torrents

# filter tohave_torrents based on what we have with some sort of logic

# download everything in tohave_torrents





