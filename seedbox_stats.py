#!/usr/bin/env python
# coding: utf-8

import sys
import datetime
import time
import lib.transmissionrpc
import urllib
import re, os
import json

servers = json.load(open(".seedboxes_logins.json", "r"))

allstats = []
for server in servers:
#     server = servers[0]

    stats = {}
    stats["time"] = time.time()
    stats["name"] = server["name"]
    
    print(stats["name"])

    try:
        client = lib.transmissionrpc.Client(address = server["host"].split(":")[0], 
                                        port=int(server["host"].split(":")[1]),
                                        user = server["account"].split(":")[0], 
                                        password = server["account"].split(":")[1])

        session = client.get_session()
        session = client.session_stats()


        stats["free_space"] = client.free_space(session.download_dir)
        stats["version"] = session._fields["version"].value
        stats["torrentCount"] = session._fields["torrentCount"].value
        stats["uploadSpeed"] = session._fields["uploadSpeed"].value
    except Exception as ex:
        stats["error"] = ex.original
    except:
        stats["error"] = sys.exc_info()[0]
#print(stats)
allstats.append(stats)


json.dump(allstats, open("seedboxes.json", "w"), indent=1)

