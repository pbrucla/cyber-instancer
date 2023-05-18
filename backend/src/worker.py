from config import rclient, config
from backend import kclient
from time import sleep, time
from kubernetes.client.exceptions import ApiException
from lock import Lock


def main():
    capi = kclient.CoreV1Api()
    while True:
        curtime = int(time())

        for chall in rclient.zrange("expiration", "-inf", curtime, byscore=True):
            print(f"[*] Deleting namespace {chall}...")
            chall = chall.decode()
            with Lock(chall):
                try:
                    capi.delete_namespace(chall)
                except ApiException as e:
                    print(f"[*] Got exception while deleting {chall}: {e}")
                rclient.zrem("expiration", chall)

        last_resync = rclient.get("last_resync")
        if (
            last_resync is None
            or int(last_resync.decode()) + config.redis_resync_interval <= curtime
        ):
            for ns in capi.list_namespace().items:
                annotations = ns.metadata.annotations
                if (
                    isinstance(annotations, dict)
                    and "instancer.acmcyber.com/chall-expires" in annotations
                ):
                    try:
                        rclient.zadd(
                            "expiration",
                            {
                                ns.metadata.name: int(
                                    annotations["instancer.acmcyber.com/chall-expires"]
                                )
                            },
                        )
                    except ValueError:
                        pass

            rclient.set("last_resync", int(time()))

        sleep(5)


if __name__ == "__main__":
    main()
