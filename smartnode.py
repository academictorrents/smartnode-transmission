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
import numpy as np
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
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            filedata = urllib.request.urlopen(req)
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
    tohave_torrents = pd.concat([tohave_torrents, a], sort=False)
    
# take union, one row per infohash. A torrent listed in several collections
# gets a different COLLECTION value per row, so dedupe on the index instead of
# on whole rows or the duplicates survive.
tohave_torrents = tohave_torrents[~tohave_torrents.index.duplicated(keep="first")]
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

# keep this much free on the filesystem at all times
space_buffer = 50 * 1024**3  # 50GB
max_torrent_size = 2000 * 1024**3   # 200GB


def human(num_bytes):
    """Format a byte count as TB/GB/MB for the log."""
    num_bytes = float(num_bytes)
    sign = "-" if num_bytes < 0 else ""
    num_bytes = abs(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return "%s%.2f %s" % (sign, num_bytes, unit)
        num_bytes /= 1024
    return "%s%.2f TB" % (sign, num_bytes)

# torrents added during this run, {hashString: SIZEBYTES}. Transmission only
# fills the drive gradually, so the bytes a torrent still has to write are not
# reflected in free_space yet. We subtract them ourselves instead of sleeping.
added_this_run = {}


def pending_bytes():
    """Bytes already committed to torrents that have not finished downloading."""
    current = client.list()
    pending = 0
    for t in current.values():
        pending += t.leftUntilDone
    # anything we just added that the daemon has not listed back yet
    known = set([t.hashString for t in current.values()])
    for hash_string, size in added_this_run.items():
        if hash_string not in known:
            pending += size
    return pending


def available_space():
    return client.free_space(download_path) - pending_bytes() - space_buffer


# Rank the download queue so the torrents closest to vanishing go first.
#   scarcity - 1/(1+seeds), steep: 0 seeds outranks 5 outranks 20.
#   demand   - log of lifetime completions plus anyone leeching right now,
#              used to break ties between equally rare torrents.
#   cost     - mild sqrt penalty on size, so a rare 10GB beats a rare 1TB.
# MIRRORS is the seed count, DOWNLOADERS is current leechers.
def priority_scores(df):
    seeds = pd.to_numeric(df.get("MIRRORS", 0), errors="coerce").fillna(0)
    completed = pd.to_numeric(df.get("TIMESCOMPLETED", 0), errors="coerce").fillna(0)
    leechers = pd.to_numeric(df.get("DOWNLOADERS", 0), errors="coerce").fillna(0)
    size = pd.to_numeric(df["SIZEBYTES"], errors="coerce").fillna(0)
    scarcity = 100.0 / (1.0 + seeds)
    demand = 1.0 + np.log10(1.0 + completed) + leechers
    cost = np.sqrt(1.0 + size / 1024.0**4)
    return scarcity * demand / cost


tohave_torrents["PRIORITY"] = priority_scores(tohave_torrents)
tohave_torrents = tohave_torrents.sort_values("PRIORITY", ascending=False)
tohave_torrents["RANK"] = range(1, len(tohave_torrents) + 1)

# print("Download priority (rarest first), top 10:")
# for _, t in tohave_torrents.head(10).iterrows():
#     print("  %4d  score %7.1f  %3d seeds  %8d downloads  %10s  %s"
#           % (t["RANK"], t["PRIORITY"], t.get("MIRRORS", 0), t.get("TIMESCOMPLETED", 0),
#              human(t["SIZEBYTES"]), str(t.get("NAME", ""))[:60]))

# add what we don't have
print("To download " + str(len(tohave_torrents.index)))
#print(tohave_torrents)
for index, torrent in tohave_torrents.iterrows():
    if torrent.name not in torrents_in_server:
        # torrent.name is the Series name, ie the INFOHASH index, not the NAME column
        print("NAME: " + str(torrent.get("NAME", "")))
        print("INFOHASH: " + torrent.name)
        print("SIZEBYTES: " + human(torrent["SIZEBYTES"]))
        print("SEEDS: %d   PRIORITY: %.1f (rank %d of %d)"
              % (torrent.get("MIRRORS", 0), torrent["PRIORITY"],
                 torrent["RANK"], len(tohave_torrents)))
        available = available_space()
        print("Available space (free - pending - buffer): " + human(available))
        if torrent["SIZEBYTES"] >= max_torrent_size:
            print("Skipping due to size")
        elif available < torrent["SIZEBYTES"]:
            print("Skipping due to space")
        else:
            url = "https://academictorrents.com/download/" + torrent.name + ".torrent"
            print(url)
            try:
                resp = requests.get(url=url, cookies=cookie_key).content
                client.add_torrent(base64.b64encode(resp).decode('utf-8'))
                added_this_run[torrent.name] = torrent["SIZEBYTES"]
#                time.sleep(1)
            except Exception as e: 
                print(e)



        
        

free_space = client.free_space(download_path)
pending = pending_bytes()
print("Free space on disk: " + human(free_space))
print("Pending downloads:  " + human(pending))
print("Buffer reserved:    " + human(space_buffer))
print("Available space:    " + human(free_space - pending - space_buffer))

# filter tohave_torrents based on what we have with some sort of logic







