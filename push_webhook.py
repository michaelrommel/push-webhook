#! /usr/bin/python3
import os
import re
import redis
from subprocess import run
from logging import getLogger, basicConfig, INFO
from signal import signal, SIGINT, SIGTERM

p = ""
mylogger = getLogger("push_webhook")


def sighandler(name, _frame):
    global p
    mylogger.warning(f"received signal {name}, graceful ending the process")
    mylogger.info("unsubscribing from channel")
    p.unsubscribe("github")


def main():
    global p
    global mylogger
    basicConfig(filename="push_webhook.log", level=INFO)
    signal(SIGINT, sighandler)
    signal(SIGTERM, sighandler)
    mylogger.info("initializing PubSub")
    pushpattern = re.compile(r"push:(?P<repo>.*)")
    khost = "192.168.30.1"
    kport = 6379
    kvstore = redis.Redis(host=khost, port=kport, db=0, decode_responses=True)
    p = kvstore.pubsub()
    mylogger.info("subscribing to channel")
    p.subscribe("github")
    for message in p.listen():
        mylogger.debug(f"received message {message}")
        if message["type"] == "message":
            m = re.match(pushpattern, message["data"])
            repo = m.group("repo")
            if repo == "michaelrommel/articles":
                mylogger.info("pulling articles repo")
                os.chdir(f"{os.environ['HOME']}/articles")
                result = run(["git", "pull"], capture_output=True, text=True)
                if result.returncode != 0:
                    mylogger.error(f"git pull failed with message {result.stderr}")
            elif repo == "rommel/journal":
                mylogger.info("pulling journal repo")
                os.chdir(f"{os.environ['HOME']}/journal")
                result = run(["git", "pull"], capture_output=True, text=True)
                if result.returncode != 0:
                    mylogger.error(f"git pull failed with message {result.stderr}")
        elif message["type"] == "unsubscribe":
            break
    mylogger.info("closing kvstore channel")
    kvstore.close()


if __name__ == "__main__":
    main()
