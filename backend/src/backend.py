from __future__ import annotations
from abc import ABC, abstractmethod
from kubernetes import client, config as kconfig
from kubernetes.client.exceptions import ApiException
from config import config, rclient, spawn_pg
from lock import Lock, LockException
from time import time
from typing import Any
import json

if config.in_cluster:
    kconfig.load_incluster_config()
else:
    kconfig.load_kube_config()


def snake_to_camel(snake: str):
    return "".join(x.capitalize() for x in snake.split("_"))


def config_to_container(cont_name: str, cfg: dict):
    kwargs = {}
    kwargs["name"] = cont_name
    kwargs["image"] = cfg["image"]
    for prop in [
        "args",
        "command",
        "image_pull_policy",
        "stdin",
        "stdin_once",
        "termination_message_path",
        "termination_message_policy",
        "tty",
        "working_dir",
    ]:
        cprop = snake_to_camel(prop)
        if cprop in cfg:
            kwargs[prop] = cfg[cprop]
    if "environment" in cfg and "env" not in cfg:
        cfg["env"] = cfg["environment"]
    if "env" in cfg:
        kwargs["env"] = [
            client.V1EnvVar(name=x["name"], value=x["value"]) for x in cfg["env"]
        ]
    for prop in [
        "env_from",
        "lifecycle",
        "liveness_probe",
        "readiness_probe",
        "startup_probe",
        "volume_devices",
        "volume_mounts",
    ]:
        if snake_to_camel(prop) in cfg:
            raise NotImplementedError(
                f"{prop} container config currently not supported"
            )
    if "kubePorts" in cfg:
        kwargs["ports"] = [client.V1ContainerPort(**x) for x in cfg["kubePorts"]]
    elif "ports" in cfg:
        kwargs["ports"] = [
            client.V1ContainerPort(container_port=x) for x in cfg["ports"]
        ]
    if "securityContext" in cfg:
        kwargs["security_context"] = client.V1SecurityContext(**cfg["securityContext"])
    if "resources" in cfg:
        kwargs["resources"] = client.V1ResourceRequirements(**cfg["resources"])
    else:
        kwargs["resources"] = client.V1ResourceRequirements(
            limits={"cpu": "500m", "memory": "512Mi"},
            requests={"cpu": "50m", "memory": "64Mi"},
        )
    return client.V1Container(**kwargs)


class Challenge(ABC):
    """A Challenge that can be started or stopped."""

    id: str
    "Challenge ID"
    lifetime: int
    "Challenge lifetime, in seconds"
    containers: dict[str, dict]
    "Mapping from container name to container config."
    exposed_ports: dict[str, list[int]]
    "Mapping from container name to list of container ports to expose"
    http_ports: dict[str, list[tuple[int, str]]]
    "Mapping from container name to list of port, subdomain pairs to expose to an HTTP proxy"
    namespace: str
    "The kubernetes namespace the challenge is running in."

    @staticmethod
    def fetch(challenge_id: str, team_id: str) -> Challenge | None:
        """Fetches the appropriate Challenge instance given challenge ID and team ID.

        Returns None if the challenge doesn't exist."""
        with spawn_pg() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT cfg, per_team, lifetime FROM challenges WHERE id=%s",
                    (challenge_id,),
                )
                result = cur.fetchone()
                if result is None:
                    return None
                cfg, per_team, lifetime = result
                if per_team:
                    return PerTeamChallenge(challenge_id, team_id, cfg, lifetime)
                else:
                    return SharedChallenge(challenge_id, cfg, lifetime)

    def expiration(self) -> int | None:
        """Returns the expiration time of a challenge as a UNIX timestamp, or None if it isn't running."""
        # Trust that the cache is correct in this case
        score = rclient.zscore("expiration", self.namespace)
        if score is None:
            return None
        return int(score)

    @abstractmethod
    def start(self):
        """Starts a challenge, or renews it if it was already running."""
        pass

    def stop(self):
        """Stops a challenge if it's running."""
        capi = client.CoreV1Api()

        print(f"[*] Deleting namespace {self.namespace}...")
        try:
            capi.delete_namespace(self.namespace)
        except ApiException as e:
            print(f"[*] Could not delete namespace {self.namespace}...")

    def port_mappings(self) -> dict[tuple[str, int], int | str] | None:
        """Return a mapping from (container name, port) pairs to either a TCP port or HTTP domain."""
        # Exit early if the container isn't running
        # This check is cached so it should be pretty quick
        if self.expiration() is None:
            return None
        cache_key = f"ports:{self.namespace}"
        cached = rclient.get(cache_key)
        if cached is not None:
            ret = {}
            parsed = json.loads(cached)
            for k, port in parsed.items():
                cont, cport = k.rsplit(":", 1)
                if isinstance(port, float):
                    port = int(port)
                ret[cont, int(cport)] = port
            return ret

        ret = {}
        capi = client.CoreV1Api()
        crdapi = client.CustomObjectsApi()

        services = capi.list_namespaced_service(self.namespace).items
        for serv in services:
            if serv.spec.type != "NodePort":
                continue
            for port in serv.spec.ports:
                ret[serv.metadata.name, port.port] = port.node_port

        ingresses = crdapi.list_namespaced_custom_object(
            "traefik.containo.us", "v1alpha1", self.namespace, "ingressroutes"
        )["items"]
        for ing in ingresses:
            http_ports = json.loads(
                ing["metadata"]["annotations"]["instancer.acmcyber.com/raw-routes"]
            )
            for port, sub in http_ports:
                ret[ing["metadata"]["name"], port] = sub

        cache_entry = {}
        for (cont, cport), port in ret.items():
            cache_entry[f"{cont}:{cport}"] = port
        rclient.set(cache_key, json.dumps(cache_entry), ex=3600)

        return ret


class SharedChallenge(Challenge):
    """A challenge with one shared instance among all teams."""

    def __init__(self, id: str, cfg: dict, lifetime: int):
        """Constructs a SharedChallenge given the challenge ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id
        self.lifetime = lifetime
        self.namespace = f"cyber-instancer-{id}"

        self.containers = cfg["containers"]
        self.exposed_ports = cfg["tcp"]
        self.http_ports = cfg["http"]

    def start(self):
        api = client.AppsV1Api()
        capi = client.CoreV1Api()
        crdapi = client.CustomObjectsApi()

        curtime = int(time())
        expiration = curtime + self.lifetime

        with Lock(self.namespace):
            try:
                curns = capi.read_namespace(self.namespace)
                print(f"[*] Renewing namespace {self.namespace}...")
                curns.metadata.annotations[
                    "instancer.acmcyber.com/chall-expires"
                ] = str(expiration)
                capi.replace_namespace(self.namespace, curns)
                rclient.zadd("expiration", {self.namespace: expiration})
                return
            except ApiException as e:
                if e.status != 404:
                    raise e
                print(f"[*] Making namespace {self.namespace}...")
                capi.create_namespace(
                    client.V1Namespace(
                        metadata=client.V1ObjectMeta(
                            name=self.namespace,
                            annotations={
                                "instancer.acmcyber.com/chall-expires": str(expiration)
                            },
                        )
                    )
                )

            rclient.zadd("expiration", {self.namespace: expiration})
            for depname, container in self.containers.items():
                print(
                    f"[*] Making deployment {depname} under namespace {self.namespace}..."
                )
                dep = client.V1Deployment(
                    metadata=client.V1ObjectMeta(
                        name=depname,
                        labels={
                            "instancer.acmcyber.com/instance-id": self.id,
                            "instancer.acmcyber.com/container-name": depname,
                        },
                    ),
                    spec=client.V1DeploymentSpec(
                        selector=client.V1LabelSelector(
                            match_labels={
                                "instancer.acmcyber.com/instance-id": self.id,
                                "instancer.acmcyber.com/container-name": depname,
                            }
                        ),
                        replicas=1,
                        template=client.V1PodTemplateSpec(
                            metadata=client.V1ObjectMeta(
                                labels={
                                    "instancer.acmcyber.com/instance-id": self.id,
                                    "instancer.acmcyber.com/container-name": depname,
                                },
                                annotations={
                                    "instancer.acmcyber.com/chall-started": str(curtime)
                                },
                            ),
                            spec=client.V1PodSpec(
                                enable_service_links=False,
                                automount_service_account_token=False,
                                containers=[config_to_container(depname, container)],
                            ),
                        ),
                    ),
                )
                api.create_namespaced_deployment(self.namespace, dep)

            for servname, container in self.containers.items():
                print(
                    f"[*] Making service {servname} under namespace {self.namespace}..."
                )
                exposed_ports = self.exposed_ports.get(servname, [])
                http_ports = self.http_ports.get(servname, [])
                if len(exposed_ports) > 0:
                    serv_spec = client.V1ServiceSpec(
                        selector={
                            "instancer.acmcyber.com/instance-id": self.id,
                            "instancer.acmcyber.com/container-name": servname,
                        },
                        ports=[
                            client.V1ServicePort(port=port, target_port=port)
                            for port in exposed_ports + [x[0] for x in http_ports]
                        ],
                        type="NodePort",
                    )
                else:
                    serv_spec = client.V1ServiceSpec(
                        selector={
                            "instancer.acmcyber.com/instance-id": self.id,
                            "instancer.acmcyber.com/container-name": servname,
                        },
                        ports=[
                            client.V1ServicePort(port=port, target_port=port)
                            for port, _ in http_ports
                        ],
                        type="ClusterIP",
                    )
                serv = client.V1Service(
                    metadata=client.V1ObjectMeta(
                        name=servname,
                        labels={
                            "instancer.acmcyber.com/instance-id": self.id,
                            "instancer.acmcyber.com/container-name": servname,
                        },
                    ),
                    spec=serv_spec,
                )
                capi.create_namespaced_service(self.namespace, serv)

            for ingname, container in self.containers.items():
                http_ports = self.http_ports.get(ingname, [])
                if len(http_ports) > 0:
                    print(
                        f"[*] Making ingress {ingname} under namespace {self.namespace}..."
                    )
                    ing = {
                        "apiVersion": "traefik.containo.us/v1alpha1",
                        "kind": "IngressRoute",
                        "metadata": {
                            "name": ingname,
                            "annotations": {
                                "instancer.acmcyber.com/raw-routes": json.dumps(
                                    http_ports
                                )
                            },
                        },
                        "spec": {
                            "entryPoints": ["web", "websecure"],
                            "routes": [
                                {
                                    "match": f"Host(`{sub}`)",
                                    "kind": "Rule",
                                    "services": [{"name": ingname, "port": port}],
                                }
                                for (port, sub) in http_ports
                            ],
                        },
                    }
                    crdapi.create_namespaced_custom_object(
                        "traefik.containo.us",
                        "v1alpha1",
                        self.namespace,
                        "ingressroutes",
                        ing,
                    )


class PerTeamChallenge(Challenge):
    """A challenge that needs to spawn a unique instance per team."""

    team_id: str

    def __init__(self, id: str, team_id: str, cfg: dict, liftime: int):
        """Constructs a PerTeamChallenge given the challenge ID and team ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id
        self.team_id = team_id
