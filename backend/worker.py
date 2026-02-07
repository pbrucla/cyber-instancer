from time import sleep, time

# For some reason mypy says kclient isn't explicitly exported even though it is
from instancer.backend import Challenge, kclient  # type: ignore[attr-defined]
from instancer.config import config, rclient
from instancer.lock import Lock
from kubernetes.client.exceptions import ApiException


def main() -> None:
    capi = kclient.CoreV1Api()
    while True:
        curtime = int(time())

        # Redis has incorrect type annotations that don't allow str
        for chall in rclient.zrange("expiration", "-inf", curtime, byscore=True):  # type: ignore[call-overload]
            Challenge.stop_namespace(chall.decode())

        last_resync = rclient.get("last_resync")
        if (
            last_resync is None
            or int(last_resync.decode()) + config.redis_resync_interval <= curtime
        ):
            expirations = {}
            boot_timestamps = {}
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
                if (
                    isinstance(annotations, dict)
                    and "instancer.acmcyber.com/chall-start-time" in annotations
                ):
                    try:
                        boot_timestamps[ns.metadata.name] = int(
                            annotations["instancer.acmcyber.com/chall-start-time"]
                        )
                    except ValueError:
                        pass

            if len(expirations) > 0:
                rclient.zadd("expiration", expirations)

            if len(boot_timestamps) > 0:
                rclient.zadd("boot_time", boot_timestamps)

            for ns in rclient.zrange("expiration", 0, -1):
                if ns.decode() not in expirations:
                    rclient.zrem("expiration", ns)

            for ns in rclient.zrange("boot_time", 0, -1):
                if ns.decode() not in boot_timestamps:
                    rclient.zrem("boot_time", ns)

            rclient.set("last_resync", int(time()))

        sleep(5)


if __name__ == "__main__":
    main()
