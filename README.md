# smartnode-transmission


Runs from a systemd timer every 12 hours. The units live in this repo and are
symlinked into /etc/systemd/system:

    ln -sf $PWD/smartnode.service /etc/systemd/system/smartnode.service
    ln -sf $PWD/smartnode.timer /etc/systemd/system/smartnode.timer
    systemctl daemon-reload
    systemctl enable --now smartnode.timer

Output goes to smartnode.log and to the journal:

    systemctl list-timers smartnode.timer     # when it next runs
    systemctl start smartnode.service         # run it now
    journalctl -u smartnode.service -f        # follow
    tail -f smartnode.log

Previously run from cron:

    0,30 * * * * cd /root/smartnode-transmission && /usr/bin/python3 smartnode.py >> /root/smartnode-transmission/smartnode.log 2>&1


# todo

- Allocate hosting based on demand
- Allocate hosting based on global coverage
- Track correct disk usage
