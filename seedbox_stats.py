#!/usr/bin/env python
# coding: utf-8

import sys
import datetime
import time
import lib.transmissionrpc
import urllib
import re, os
import json


def humanbytes(B):
    B = float(B)
    KB = float(1000)
    MB = float(KB ** 2)
    GB = float(KB ** 3)
    TB = float(KB ** 4)

    if B < KB:
        return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
    elif KB <= B < MB:
        return '{0:.2f} KB'.format(B/KB)
    elif MB <= B < GB:
        return '{0:.2f} MB'.format(B/MB)
    elif GB <= B < TB:
        return '{0:.2f} GB'.format(B/GB)
    elif TB <= B:
        return '{0:.2f} TB'.format(B/TB)



print(sys.argv[1])

servers = json.load(open(".seedboxes_logins.json", "r"))

allstats = []
for server in servers:
#     server = servers[0]

    stats = {}
    stats["time"] = time.time()
    stats["ctime"] = time.ctime()
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
        stats["free_space_human"] = humanbytes(stats["free_space"])
        stats["version"] = session._fields["version"].value
        stats["torrentCount"] = session._fields["torrentCount"].value
        stats["uploadSpeed"] = session._fields["uploadSpeed"].value
        stats["uploadSpeed_human"] = "{}/s".format(humanbytes(stats["uploadSpeed"]))
    except Exception as ex:
        stats["error"] = str(ex.original)
    except:
        stats["error"] = str(sys.exc_info()[0])
        
    #print(stats)
    allstats.append(stats)


json.dump(allstats, open(sys.argv[1] + "seedboxes.json", "w"), indent=1)

