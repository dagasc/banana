<b>Banana Python3 Lightweight IRC Bot</b>

Features:
- ADMIN invite-only channel joining
- VHOST support via PERFORM: `/vhost <user> <pass>`
- CTCP support: VERSION and PING with flood protection

<b>Start</b>: `nohup python3 banana.py &`

<b>Kill</b>: `pkill -f banana.py`

<b>Crontab:</b>

`@reboot sleep 10 && cd /path/to/script && nohup python3 banana.py >/tmp/banana.log 2>&1 &`

`*/5 * * * * pgrep -f "python3 banana.py" >/dev/null || cd /path/to/script && nohup python3 banana.py >/tmp/banana.log 2>&1 &`
