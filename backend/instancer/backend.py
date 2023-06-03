from __future__ import annotations

import json
import random
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from time import time
from typing import Any, cast

from kubernetes import client as kclient
from kubernetes import config as kconfig
from kubernetes.client.exceptions import ApiException
from psycopg.types.json import Jsonb

from instancer.config import config, connect_pg, rclient
from instancer.lock import Lock, LockException

CHALL_CACHE_TIME = 3600

if config.in_cluster:
    kconfig.load_incluster_config()
else:
    kconfig.load_kube_config()


def snake_to_camel(snake: str) -> str:
    return "".join(x.capitalize() for x in snake.lower().split("_"))


def camel_to_snake(camel: str) -> str:
    return re.sub(r"\B([A-Z])", r"_\1", camel).lower()


def keys_to_snake(d: dict[str, Any]) -> dict[str, Any]:
    return {camel_to_snake(k): v for (k, v) in d.items()}


def config_to_container(
    cont_name: str, cfg: dict[str, Any], env_metadata: Any = None
) -> kclient.V1Container:
    kwargs: dict[str, Any] = {}
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
    env = [
        kclient.V1EnvVar(name=x["name"], value=x["value"])
        for x in cfg.get("env", []) + cfg.get("environment", [])
    ]
    if env_metadata is not None and not any(
        x.name == "INSTANCER_METADATA" for x in env
    ):
        env.append(
            kclient.V1EnvVar(name="INSTANCER_METADATA", value=json.dumps(env_metadata))
        )
    kwargs["env"] = env
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
    ports: list[kclient.V1ContainerPort] = []
    if "kubePorts" in cfg:
        ports.extend(
            kclient.V1ContainerPort(**keys_to_snake(x)) for x in cfg["kubePorts"]
        )
    if "ports" in cfg:
        ports.extend(kclient.V1ContainerPort(container_port=x) for x in cfg["ports"])
    kwargs["ports"] = ports
    if "securityContext" in cfg:
        kwargs["security_context"] = kclient.V1SecurityContext(
            **keys_to_snake(cfg["securityContext"])
        )
    if "resources" in cfg:
        kwargs["resources"] = kclient.V1ResourceRequirements(
            **keys_to_snake(cfg["resources"])
        )
    else:
        kwargs["resources"] = kclient.V1ResourceRequirements(
            limits={"cpu": "500m", "memory": "512Mi"},
            requests={"cpu": "50m", "memory": "64Mi"},
        )
    return kclient.V1Container(**kwargs)


class ResourceUnavailableError(Exception):
    """Error thrown when a resource is temporarily unavailable.

    For example: a namespace is locked or terminating."""

    pass


@dataclass
class ChallengeTag:
    """A challenge tag."""

    name: str
    "The name of the tag."
    is_category: bool
    "Whether the tag is a challenge category."


@dataclass
class ChallengeMetadata:
    """Metadata of a challenge including the challenge name, description, and author."""

    name: str
    "The challenge name."
    description: str
    "The challenge description."
    author: str
    "The challenge author."


@dataclass
class DeploymentInfo:
    """The expiration time and port mappings of a deployment."""

    expiration: int
    "The expiration time."
    port_mappings: dict[tuple[str, int], int | str]
    "Mapping from a tuple of the container name and internal port to the external port or HTTPS domain."


def _make_challenge(
    chall_id: str,
    cfg: dict[str, Any],
    per_team: bool,
    lifetime: int,
    name: str,
    description: str,
    author: str,
    team_id: str,
) -> Challenge:
    metadata = ChallengeMetadata(name, description, author)
    if per_team:
        return PerTeamChallenge(chall_id, team_id, cfg, lifetime, metadata)
    else:
        return SharedChallenge(chall_id, cfg, lifetime, metadata)


class Challenge(ABC):
    """A Challenge that can be started or stopped."""

    id: str
    "Challenge ID"
    lifetime: int
    "Challenge lifetime, in seconds"
    metadata: ChallengeMetadata
    "Challenge metadata"
    containers: dict[str, dict[str, Any]]
    "Mapping from container name to container config."
    exposed_ports: dict[str, list[int]]
    "Mapping from container name to list of container ports to expose"
    http_ports: dict[str, list[tuple[int, str]]]
    "Mapping from container name to list of port, subdomain pairs to expose to an HTTP proxy"
    namespace: str
    "The kubernetes namespace the challenge is running in."
    additional_labels: dict[str, Any]
    "Additional labels for the challenge deployments."
    additional_env_metadata: dict[str, Any]
    "Additional metadata to put in challenge environment variables."

    def __init__(
        self,
        chall_id: str,
        cfg: dict[str, Any],
        lifetime: int,
        metadata: ChallengeMetadata,
        *,
        namespace: str,
        exposed_ports: dict[str, list[int]],
        http_ports: dict[str, list[tuple[int, str]]],
        additional_labels: dict[str, Any] = {},
        additional_env_metadata: dict[str, Any] = {},
    ):
        self.id = chall_id
        self.lifetime = lifetime
        self.metadata = metadata
        if len(namespace) > 63:
            namespace = "ci-" + sha256(namespace.encode()).hexdigest()[:60]
        self.namespace = namespace
        self.containers = cfg["containers"]
        self.exposed_ports = exposed_ports
        self.http_ports = http_ports
        self.additional_labels = additional_labels
        self.additional_env_metadata = additional_env_metadata

    def is_running(self) -> bool:
        return self.expiration() is not None

    @staticmethod
    def create(
        chall_id: str,
        per_team: bool,
        cfg: dict[str, Any],
        lifetime: int,
        metadata: ChallengeMetadata,
        tags: list[ChallengeTag],
    ) -> None:
        """Create a new challenge and insert it into the database."""

        with connect_pg() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    (
                        "INSERT INTO challenges (id, cfg, per_team, lifetime, name, description, author) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        chall_id,
                        Jsonb(cfg),
                        per_team,
                        lifetime,
                        metadata.name,
                        metadata.description,
                        metadata.author,
                    ),
                )
                with cur.copy(
                    "COPY tags (challenge_id, name, is_category) FROM STDIN"
                ) as copy:
                    for tag in tags:
                        copy.write_row((chall_id, tag.name, tag.is_category))
        rclient.delete("all_challs")

    @staticmethod
    def delete(chall_id: str) -> bool:
        """Delete a challenge.

        Returns True if the challenge was deleted and False if the challenge doesn't exist.
        """

        with connect_pg() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tags WHERE challenge_id=%s", (chall_id,))
                cur.execute("DELETE FROM challenges WHERE id=%s", (chall_id,))
                if cur.rowcount < 1:
                    return False
        rclient.delete("all_challs")
        rclient.delete(f"chall:{chall_id}")
        rclient.delete(f"chall_tags:{chall_id}")
        return True

    @classmethod
    def fetchall(cls, team_id: str) -> list[tuple[Challenge, list[ChallengeTag]]]:
        """Fetch all challenges, including categories and tags.

        Returns a list where each element is a tuple of a Challenge and its tags.
        Challenges are returned in an unspecified order.
        """

        cache_key = "all_challs"
        cached = rclient.get(cache_key)
        if cached is not None:
            challenge_ids = json.loads(cached)
            result: list[tuple[Challenge, list[ChallengeTag]]] = []
            for chall_id in challenge_ids:
                chall = cls.fetch(chall_id, team_id)
                if chall is not None:
                    result.append((chall, chall.tags()))
            return result
        else:
            with connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, cfg, per_team, lifetime, name, description, author FROM challenges"
                    )
                    all_challs: list[
                        tuple[str, dict[str, Any], bool, int, str, str, str]
                    ] = cur.fetchall()
                    cur.execute(
                        "SELECT challenge_id, name, is_category FROM tags ORDER BY is_category DESC, name"
                    )
                    all_tags: list[tuple[str, str, bool]] = cur.fetchall()
            rclient.set(
                cache_key,
                json.dumps([chall_id for (chall_id, *_) in all_challs]),
                ex=CHALL_CACHE_TIME,
            )
            tags: dict[str, list[ChallengeTag]] = defaultdict(list)
            for chall_id, name, is_category in all_tags:
                tags[chall_id].append(ChallengeTag(name, is_category))
            return [
                (
                    _make_challenge(*chall_data, team_id),
                    tags.get(chall_data[0], []),
                )
                for chall_data in all_challs
            ]

    @staticmethod
    def fetch(challenge_id: str, team_id: str) -> Challenge | None:
        """Fetches the appropriate Challenge instance given challenge ID and team ID.

        Returns None if the challenge doesn't exist."""
        cache_key = f"chall:{challenge_id}"
        cached = rclient.get(cache_key)
        if cached is not None:
            result = cast(
                tuple[dict[str, Any], bool, int, str, str, str],
                tuple(json.loads(cached)),
            )
        else:
            with connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT cfg, per_team, lifetime, name, description, author FROM challenges WHERE id=%s",
                        (challenge_id,),
                    )
                    result = cast(
                        tuple[dict[str, Any], bool, int, str, str, str], cur.fetchone()
                    )
            rclient.set(cache_key, json.dumps(result), ex=CHALL_CACHE_TIME)

        if result is None:
            return None
        return _make_challenge(challenge_id, *result, team_id)

    def tags(self) -> list[ChallengeTag]:
        """Return a list of tags for the challenge.

        The category tags will be listed first and tags will be sorted alphabetically.
        """

        cache_key = f"chall_tags:{self.id}"
        cached = rclient.get(cache_key)

        if cached is not None:
            result = json.loads(cached)
        else:
            with connect_pg() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT name, is_category FROM tags WHERE challenge_id=%s ORDER BY is_category DESC, name",
                        (self.id,),
                    )
                    result = cur.fetchall()
            rclient.set(cache_key, json.dumps(result), ex=CHALL_CACHE_TIME)

        return [ChallengeTag(*tag) for tag in result]

    def expiration(self) -> int | None:
        """Returns the expiration time of a challenge as a UNIX timestamp, or None if it isn't running."""
        # Trust that the cache is correct in this case
        score = rclient.zscore("expiration", self.namespace)
        if score is None:
            return None
        return int(score)

    @abstractmethod
    def is_shared(self) -> bool:
        """Returns True if challenge is shared, e.g. should not be terminatable"""
        raise NotImplementedError

    def start(self) -> None:
        """Starts a challenge, or renews it if it was already running."""
        api = kclient.AppsV1Api()
        capi = kclient.CoreV1Api()
        crdapi = kclient.CustomObjectsApi()
        napi = kclient.NetworkingV1Api()

        curtime = int(time())
        expiration = curtime + self.lifetime

        env_metadata = {
            "namespace": self.namespace,
            "instance_id": self.id,
            "http": {
                contname: {
                    port: sub
                    for (
                        port,
                        sub,
                    ) in self.http_ports.get(contname, [])
                }
                for contname in self.containers
            },
            **self.additional_env_metadata,
        }

        common_labels = {
            "instancer.acmcyber.com/instance-id": self.id,
            **self.additional_labels,
        }

        namespace_made = False

        try:
            with Lock(self.namespace):
                try:
                    curns = capi.read_namespace(self.namespace)
                    if curns.status.phase == "Terminating":
                        raise ResourceUnavailableError(
                            f"namespace {self.namespace} is still terminating"
                        )
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
                                    "instancer.acmcyber.com/chall-expires": str(
                                        expiration
                                    ),
                                },
                                labels=common_labels,
                            )
                        )
                    )

                namespace_made = True
                rclient.zadd("expiration", {self.namespace: expiration})
                for depname, container in self.containers.items():
                    print(
                        f"[*] Making deployment {depname} under namespace {self.namespace}..."
                    )
                    labels = {
                        **common_labels,
                        "instancer.acmcyber.com/container-name": depname,
                    }
                    pod_labels = {
                        **labels,
                        "instancer.acmcyber.com/has-egress": "true"
                        if container.get("hasEgress", True)
                        else "false",
                        "instancer.acmcyber.com/has-ingress": "true"
                        if len(self.exposed_ports.get(depname, [])) > 0
                        or len(self.http_ports.get(depname, [])) > 0
                        else "false",
                    }
                    dep = kclient.V1Deployment(
                        metadata=kclient.V1ObjectMeta(
                            name=depname,
                            labels=labels,
                        ),
                        spec=kclient.V1DeploymentSpec(
                            selector=kclient.V1LabelSelector(match_labels=pod_labels),
                            replicas=1,
                            template=kclient.V1PodTemplateSpec(
                                metadata=kclient.V1ObjectMeta(
                                    labels=pod_labels,
                                    annotations={
                                        "instancer.acmcyber.com/chall-started": str(
                                            curtime
                                        )
                                    },
                                ),
                                spec=kclient.V1PodSpec(
                                    enable_service_links=False,
                                    automount_service_account_token=False,
                                    containers=[
                                        config_to_container(
                                            depname,
                                            container,
                                            env_metadata={
                                                "container_name": depname,
                                                **env_metadata,
                                            },
                                        )
                                    ],
                                ),
                            ),
                        ),
                    )
                    api.create_namespaced_deployment(self.namespace, dep)

                for servname, container in self.containers.items():
                    exposed_ports = self.exposed_ports.get(servname, [])
                    http_ports = self.http_ports.get(servname, [])
                    private_ports = container.get("ports", []) + [
                        x["containerPort"] for x in container.get("kubePorts", [])
                    ]
                    private_ports = [x for x in private_ports if x not in exposed_ports]
                    multiservice = len(exposed_ports) > 0 and len(private_ports) > 0
                    selector = {
                        **common_labels,
                        "instancer.acmcyber.com/container-name": servname,
                    }
                    serv_specs = []
                    if len(exposed_ports) > 0:
                        serv_specs.append(
                            kclient.V1ServiceSpec(
                                selector=selector,
                                ports=[
                                    kclient.V1ServicePort(port=port, target_port=port)
                                    for port in exposed_ports
                                ],
                                type="NodePort",
                            )
                        )
                    if len(private_ports) > 0:
                        serv_specs.append(
                            kclient.V1ServiceSpec(
                                selector=selector,
                                ports=[
                                    kclient.V1ServicePort(port=port, target_port=port)
                                    for port in private_ports
                                ],
                                type="ClusterIP",
                            )
                        )
                    for serv_spec in serv_specs:
                        print(
                            f"[*] Making service {servname} under namespace {self.namespace}..."
                        )
                        serv = kclient.V1Service(
                            metadata=kclient.V1ObjectMeta(
                                name=servname + "-instancer-external"
                                if multiservice and serv_spec.type == "NodePort"
                                else servname,
                                labels={
                                    **common_labels,
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
                                "labels": {
                                    **common_labels,
                                    "instancer.acmcyber.com/container-name": ingname,
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

                pol_interns = kclient.V1NetworkPolicy(
                    metadata=kclient.V1ObjectMeta(name="interns", labels=common_labels),
                    spec=kclient.V1NetworkPolicySpec(
                        pod_selector=kclient.V1LabelSelector(),
                        policy_types=["Ingress", "Egress"],
                        ingress=[
                            # allow ingress from other pods in the namespace
                            kclient.V1NetworkPolicyIngressRule(
                                _from=[
                                    kclient.V1NetworkPolicyPeer(
                                        namespace_selector=kclient.V1LabelSelector(
                                            match_labels=common_labels
                                        )
                                    )
                                ]
                            )
                        ],
                        egress=[
                            # allow egress to other pods in the namespace
                            kclient.V1NetworkPolicyEgressRule(
                                to=[
                                    kclient.V1NetworkPolicyPeer(
                                        namespace_selector=kclient.V1LabelSelector(
                                            match_labels=common_labels
                                        )
                                    )
                                ]
                            ),
                            # allow egress to the cluster's dns server
                            kclient.V1NetworkPolicyEgressRule(
                                to=[
                                    kclient.V1NetworkPolicyPeer(
                                        namespace_selector=kclient.V1LabelSelector(
                                            match_labels={
                                                "kubernetes.io/metadata.name": "kube-system"
                                            }
                                        )
                                    )
                                ],
                                ports=[
                                    kclient.V1NetworkPolicyPort(port=53, protocol="UDP")
                                ],
                            ),
                        ],
                    ),
                )
                pol_ingress = kclient.V1NetworkPolicy(
                    metadata=kclient.V1ObjectMeta(name="ingress", labels=common_labels),
                    spec=kclient.V1NetworkPolicySpec(
                        pod_selector=kclient.V1LabelSelector(
                            match_labels={"instancer.acmcyber.com/has-ingress": "true"}
                        ),
                        policy_types=["Ingress"],
                        ingress=[
                            # allow ingress from anyone
                            kclient.V1NetworkPolicyIngressRule(
                                _from=[
                                    kclient.V1NetworkPolicyPeer(
                                        ip_block=kclient.V1IPBlock(cidr="0.0.0.0/0")
                                    )
                                ]
                            )
                        ],
                    ),
                )
                pol_egress = kclient.V1NetworkPolicy(
                    metadata=kclient.V1ObjectMeta(name="egress", labels=common_labels),
                    spec=kclient.V1NetworkPolicySpec(
                        pod_selector=kclient.V1LabelSelector(
                            match_labels={"instancer.acmcyber.com/has-egress": "true"}
                        ),
                        policy_types=["Egress"],
                        egress=[
                            # allow egress to anyone except IANA private IP blocks
                            kclient.V1NetworkPolicyEgressRule(
                                to=[
                                    kclient.V1NetworkPolicyPeer(
                                        ip_block=kclient.V1IPBlock(
                                            cidr="0.0.0.0/0",
                                            _except=[
                                                "10.0.0.0/8",
                                                "172.16.0.0/12",
                                                "192.168.0.0/16",
                                                "169.254.0.0/16",
                                            ],
                                        )
                                    )
                                ]
                            )
                        ],
                    ),
                )
                print(
                    f"[*] Making network policies under namespace {self.namespace}..."
                )
                napi.create_namespaced_network_policy(self.namespace, pol_interns)
                napi.create_namespaced_network_policy(self.namespace, pol_ingress)
                napi.create_namespaced_network_policy(self.namespace, pol_egress)
        except LockException:
            raise ResourceUnavailableError(f"namespace {self.namespace} is locked")
        except Exception:
            if namespace_made:
                print(f"[*] Got error, cleaning up namespace {self.namespace}...")
                try:
                    capi.delete_namespace(self.namespace)
                    rclient.zrem("expiration", self.namespace)
                except ApiException:
                    print(f"[*] Could not clean up namespace {self.namespace}...")
            raise

    @staticmethod
    def stop_namespace(namespace: str) -> None:
        """Stops a challenge given the namespace of the challenge."""
        capi = kclient.CoreV1Api()

        print(f"[*] Deleting namespace {namespace}...")
        try:
            capi.delete_namespace(namespace)
            rclient.zrem("expiration", namespace)
            rclient.delete(f"ports:{namespace}")
        except ApiException as e:
            if e.status == 404:
                print(
                    f"[*] Could not delete namespace {namespace} because namespace does not exist..."
                )
            else:
                print(f"[*] Could not delete namespace {namespace} due to error {e}...")

    def stop(self) -> None:
        """Stops a challenge if it's running."""
        self.stop_namespace(self.namespace)

    def deployment_status(self) -> DeploymentInfo | None:
        """Return the challenge deployment info, or None if the challenge isn't deployed."""
        # Exit early if the container isn't running
        # This check is cached so it should be pretty quick
        exp = self.expiration()
        if exp is None:
            return None
        cache_key = f"ports:{self.namespace}"
        cached = rclient.get(cache_key)

        port_mappings = {}

        if cached is not None:
            parsed = json.loads(cached)
            for k, port in parsed.items():
                cont, cport = k.rsplit(":", 1)
                if isinstance(port, float):
                    port = int(port)
                port_mappings[cont, int(cport)] = port
            return DeploymentInfo(exp, port_mappings)

        capi = kclient.CoreV1Api()
        crdapi = kclient.CustomObjectsApi()

        services = capi.list_namespaced_service(self.namespace).items
        for serv in services:
            if serv.spec.type != "NodePort":
                continue
            for port in serv.spec.ports:
                port_mappings[serv.metadata.name, port.port] = port.node_port

        ingresses = crdapi.list_namespaced_custom_object(
            "traefik.containo.us", "v1alpha1", self.namespace, "ingressroutes"
        )["items"]
        for ing in ingresses:
            http_ports = json.loads(
                ing["metadata"]["annotations"]["instancer.acmcyber.com/raw-routes"]
            )
            for port, sub in http_ports:
                port_mappings[ing["metadata"]["name"], port] = sub

        cache_entry = {}
        for (cont, cport), port in port_mappings.items():
            cache_entry[f"{cont}:{cport}"] = port
        t = int(time())
        if exp > t:
            rclient.set(cache_key, json.dumps(cache_entry), ex=exp - t)

        return DeploymentInfo(exp, port_mappings)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(namespace={self.namespace!r}, expiration={self.expiration()!r})"


class SharedChallenge(Challenge):
    """A challenge with one shared instance among all teams."""

    def __init__(
        self, id: str, cfg: dict[str, Any], lifetime: int, metadata: ChallengeMetadata
    ):
        """Constructs a SharedChallenge given the challenge ID.

        Do not call this constructor directly; use Challenge.fetch instead.
        """

        super().__init__(
            id,
            cfg,
            lifetime,
            metadata,
            namespace=f"ci-{id}",
            exposed_ports=cfg.get("tcp", {}),
            http_ports=cfg.get("http", {}),
        )

    def is_shared(self) -> bool:
        """Returns True if challenge is shared, e.g. should not be terminatable"""
        return True


class PerTeamChallenge(Challenge):
    """A challenge that needs to spawn a unique instance per team."""

    team_id: str

    def __init__(
        self,
        id: str,
        team_id: str,
        cfg: dict[str, Any],
        lifetime: int,
        metadata: ChallengeMetadata,
    ):
        """Constructs a PerTeamChallenge given the challenge ID and team ID.

        Do not call this constructor directly; use Challenge.fetch instead.
        """

        http_ports = {}
        for cont_name, ports in cfg.get("http", {}).items():
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
            namespace=f"ci-{id}-t-{team_id.replace('-', '')}",
            exposed_ports=cfg.get("tcp", {}),
            http_ports=http_ports,
            additional_labels={"instancer.acmcyber.com/team-id": team_id},
            additional_env_metadata={"team_id": team_id},
        )

        self.team_id = team_id

    def is_shared(self) -> bool:
        """Returns True if challenge is shared, e.g. should not be terminatable"""
        return False
