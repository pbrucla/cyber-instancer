from config import rclient, config
from backend import Challenge
from kubernetes import client as kclient
from time import sleep, time
from kubernetes.client.exceptions import ApiException
from typing import Module


def main():
    capi = kclient.CoreV1Api()
    while True:
        for chall in rclient.zrange("expiration", int(time()), "+inf", byscore=True):
            chall = chall.decode()
            try:
                capi.delete_namespace(chall)
            except ApiException as e:
                print(f"[*] Got exception while deleting {chall}: {e}")
            rclient.zrem(chall)

        sleep(5)


if __name__ == "__main__":
    main()
