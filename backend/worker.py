from instancer.config import rclient, config
from instancer.backend import kclient, Challenge
from time import sleep, time
from kubernetes.client.exceptions import ApiException
from instancer.lock import Lock


def main():
    capi = kclient.CoreV1Api()
    while True:
        curtime = int(time())

        for chall in rclient.zrange("expiration", "-inf", curtime, byscore=True):
            Challenge.stop_namespace(chall.decode())

        last_resync = rclient.get("last_resync")
        if (
            last_resync is None
            or int(last_resync.decode()) + config.redis_resync_interval <= curtime
        ):
            expirations = {}
            for ns in capi.list_namespace().items:
                annotations = ns.metadata.annotations
                if (
                    isinstance(annotations, dict)
                    and "instancer.acmcyber.com/chall-expires" in annotations
                ):
                    try:
                        expirations[ns.metadata.name] = int(
                            annotations["instancer.acmcyber.com/chall-expires"]
                        )
                    except ValueError:
                        pass

            if len(expirations) > 0:
                rclient.zadd("expiration", expirations)

            for ns in rclient.zrange("expiration", 0, -1):
                if ns.decode() not in expirations:
                    rclient.zrem("expiration", ns)

            rclient.set("last_resync", int(time()))

        sleep(5)


if __name__ == "__main__":
    main()
