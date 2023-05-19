from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from kubernetes import client as kclient, config as kconfig
from kubernetes.client.exceptions import ApiException
from instancer.config import config, rclient, pg_pool
from instancer.lock import Lock, LockException
from time import time
import random
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
            kclient.V1EnvVar(name=x["name"], value=x["value"]) for x in cfg["env"]
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
        kwargs["ports"] = [kclient.V1ContainerPort(**x) for x in cfg["kubePorts"]]
    elif "ports" in cfg:
        kwargs["ports"] = [
            kclient.V1ContainerPort(container_port=x) for x in cfg["ports"]
        ]
    if "securityContext" in cfg:
        kwargs["security_context"] = kclient.V1SecurityContext(**cfg["securityContext"])
    if "resources" in cfg:
        kwargs["resources"] = kclient.V1ResourceRequirements(**cfg["resources"])
    else:
        kwargs["resources"] = kclient.V1ResourceRequirements(
            limits={"cpu": "500m", "memory": "512Mi"},
            requests={"cpu": "50m", "memory": "64Mi"},
        )
    return kclient.V1Container(**kwargs)


@dataclass
class ChallengeMetadata:
    """Metadata of a challenge including the challenge name, description, and author."""

    name: str
    "The challenge name."
    description: str
    "The challenge description."
    author: str
    "The challenge author."


class Challenge(ABC):
    """A Challenge that can be started or stopped."""

    id: str
    "Challenge ID"
    lifetime: int
    "Challenge lifetime, in seconds"
    metadata: ChallengeMetadata
    "Challenge metadata"
    containers: dict[str, dict]
    "Mapping from container name to container config."
    exposed_ports: dict[str, list[int]]
    "Mapping from container name to list of container ports to expose"
    http_ports: dict[str, list[tuple[int, str]]]
    "Mapping from container name to list of port, subdomain pairs to expose to an HTTP proxy"
    namespace: str
    "The kubernetes namespace the challenge is running in."
    additional_labels: dict
    "Additional labels for the challenge deployments."

    def __init__(
        self,
        id: str,
        cfg: dict[str, Any],
        lifetime: int,
        metadata: ChallengeMetadata,
        *,
        namespace: str,
        exposed_ports: dict[str, list[int]],
        http_ports: dict[str, list[tuple[int, str]]],
        additional_labels: dict[str, Any],
    ):
        self.id = id
        self.lifetime = lifetime
        self.metadata = metadata
        self.namespace = namespace
        self.containers = cfg["containers"]
        self.exposed_ports = exposed_ports
        self.http_ports = http_ports
        self.additional_labels = additional_labels

    @staticmethod
    def fetch(challenge_id: str, team_id: str) -> Challenge | None:
        """Fetches the appropriate Challenge instance given challenge ID and team ID.

        Returns None if the challenge doesn't exist."""
        cache_key = f"chall:{challenge_id}"
        cached = rclient.get(cache_key)
        if cached is not None:
            result = json.loads(cached)
        else:
            with pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT cfg, per_team, lifetime, name, description, author FROM challenges WHERE id=%s",
                        (challenge_id,),
                    )
                    result = cur.fetchone()
            rclient.set(cache_key, json.dumps(result), ex=3600)

        if result is None:
            return None
        cfg, per_team, lifetime, name, description, author = result
        metadata = ChallengeMetadata(name, description, author)
        if per_team:
            return PerTeamChallenge(challenge_id, team_id, cfg, lifetime, metadata)
        else:
            return SharedChallenge(challenge_id, cfg, lifetime, metadata)

    def tags(self) -> tuple[list[str], list[str]]:
        """Return a tuple of a list of category tags and a list of other tags.

        Tags will be sorted in alphabetical order.
        """

        cache_key = f"chall_tags:{self.id}"
        cached = rclient.get(cache_key)

        if cached is not None:
            categories, other_tags = json.loads(cached)
        else:
            with pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT name FROM tags WHERE challenge_id=%s AND is_category=true ORDER BY name",
                        (self.id,),
                    )
                    categories = [category for category, in cur.fetchall()]
                    cur.execute(
                        "SELECT name FROM tags WHERE challenge_id=%s AND is_category=false ORDER BY name",
                        (self.id,),
                    )
                    other_tags = [tag for tag, in cur.fetchall()]
            rclient.set(cache_key, json.dumps((categories, other_tags)), ex=3600)

        return categories, other_tags

    def expiration(self) -> int | None:
        """Returns the expiration time of a challenge as a UNIX timestamp, or None if it isn't running."""
        # Trust that the cache is correct in this case
        score = rclient.zscore("expiration", self.namespace)
        if score is None:
            return None
        return int(score)

    def start(self):
        """Starts a challenge, or renews it if it was already running."""
        api = kclient.AppsV1Api()
        capi = kclient.CoreV1Api()
        crdapi = kclient.CustomObjectsApi()

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
                    kclient.V1Namespace(
                        metadata=kclient.V1ObjectMeta(
                            name=self.namespace,
                            annotations={
                                "instancer.acmcyber.com/chall-expires": str(expiration),
                            },
                            labels={
                                "instancer.acmcyber.com/instance-id": self.id,
                                **self.additional_labels,
                            },
                        )
                    )
                )

            rclient.zadd("expiration", {self.namespace: expiration})
            for depname, container in self.containers.items():
                print(
                    f"[*] Making deployment {depname} under namespace {self.namespace}..."
                )
                labels = {
                    "instancer.acmcyber.com/instance-id": self.id,
                    "instancer.acmcyber.com/container-name": depname,
                    **self.additional_labels,
                }
                dep = kclient.V1Deployment(
                    metadata=kclient.V1ObjectMeta(
                        name=depname,
                        labels=labels,
                    ),
                    spec=kclient.V1DeploymentSpec(
                        selector=kclient.V1LabelSelector(match_labels=labels),
                        replicas=1,
                        template=kclient.V1PodTemplateSpec(
                            metadata=kclient.V1ObjectMeta(
                                labels=labels,
                                annotations={
                                    "instancer.acmcyber.com/chall-started": str(curtime)
                                },
                            ),
                            spec=kclient.V1PodSpec(
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
                selector = {
                    "instancer.acmcyber.com/instance-id": self.id,
                    "instancer.acmcyber.com/container-name": servname,
                    **self.additional_labels,
                }
                if len(exposed_ports) > 0:
                    serv_spec = kclient.V1ServiceSpec(
                        selector=selector,
                        ports=[
                            kclient.V1ServicePort(port=port, target_port=port)
                            for port in exposed_ports + [x[0] for x in http_ports]
                        ],
                        type="NodePort",
                    )
                else:
                    serv_spec = kclient.V1ServiceSpec(
                        selector=selector,
                        ports=[
                            kclient.V1ServicePort(port=port, target_port=port)
                            for port, _ in http_ports
                        ],
                        type="ClusterIP",
                    )
                serv = kclient.V1Service(
                    metadata=kclient.V1ObjectMeta(
                        name=servname,
                        labels={
                            "instancer.acmcyber.com/instance-id": self.id,
                            "instancer.acmcyber.com/container-name": servname,
                            **self.additional_labels,
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
                            "labels": {
                                "instancer.acmcyber.com/instance-id": self.id,
                                "instancer.acmcyber.com/container-name": ingname,
                                **self.additional_labels,
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

    def stop(self):
        """Stops a challenge if it's running."""
        capi = kclient.CoreV1Api()

        print(f"[*] Deleting namespace {self.namespace}...")
        try:
            capi.delete_namespace(self.namespace)
            rclient.zrem("expiration", self.namespace)
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
        capi = kclient.CoreV1Api()
        crdapi = kclient.CustomObjectsApi()

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

    def __repr__(self) -> str:
        return f"{type(self).__name__}(namespace={self.namespace!r}, expiration={self.expiration()!r})"


class SharedChallenge(Challenge):
    """A challenge with one shared instance among all teams."""

    def __init__(self, id: str, cfg: dict, lifetime: int, metadata: ChallengeMetadata):
        """Constructs a SharedChallenge given the challenge ID.

        Do not call this constructor directly; use Challenge.fetch instead.
        """

        super().__init__(
            id,
            cfg,
            lifetime,
            metadata,
            namespace=f"chall-instance-{id}",
            exposed_ports=cfg["tcp"],
            http_ports=cfg["http"],
            additional_labels={},
        )


class PerTeamChallenge(Challenge):
    """A challenge that needs to spawn a unique instance per team."""

    team_id: str

    def __init__(
        self,
        id: str,
        team_id: str,
        cfg: dict,
        lifetime: int,
        metadata: ChallengeMetadata,
    ):
        """Constructs a PerTeamChallenge given the challenge ID and team ID.

        Do not call this constructor directly; use Challenge.fetch instead.
        """

        http_ports = {}
        for cont_name, ports in cfg["http"].items():
            l = []
            for port, domain in ports:
                chunks = domain.split(".")
                chunks[0] += "-" + "".join(
                    random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=5)
                )
                l.append((port, ".".join(chunks)))
            http_ports[cont_name] = l

        super().__init__(
            id,
            cfg,
            lifetime,
            metadata,
            namespace=f"chall-instance-{id}-team-{team_id}",
            exposed_ports=cfg["tcp"],
            http_ports=http_ports,
            additional_labels={"instancer.acmcyber.com/team-id": team_id},
        )

        self.team_id = team_id
