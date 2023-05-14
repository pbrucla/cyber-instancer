from __future__ import annotations
from abc import ABC, abstractmethod
from kubernetes import client, config as kconfig
from kubernetes.client.exceptions import ApiException
from config import config, rclient
from lock import Lock, LockException
from time import time
from typing import Any

if config.in_cluster:
    kconfig.load_incluster_config()
else:
    kconfig.load_kube_config()


def snake_to_camel(snake: str):
    return "".join(x.capitalize() for x in snake.split("_"))


def config_to_container(cont_name: str, cfg: dict):
    kube = cfg["kube"]
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
        if cprop in kube:
            kwargs[prop] = kube[cprop]
    if "environment" in kube and "env" not in kube:
        kube["env"] = kube["environment"]
    if "env" in kube:
        kwargs["env"] = [
            client.V1EnvVar(name=x["name"], value=x["value"]) for x in kube["env"]
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
        if snake_to_camel(prop) in kube:
            raise NotImplementedError(
                f"{prop} container config currently not supported"
            )
    if "ports" in kube:
        kwargs["ports"] = [client.V1ContainerPort(**x) for x in kube["ports"]]
    if "securityContext" in kube:
        kwargs["security_context"] = client.V1SecurityContext(**kube["securityContext"])
    if "resources" in kube:
        kwargs["resources"] = client.V1ResourceRequirements(**kube["resources"])
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
    http_ports: dict[str, list[(int, str)]]
    "Mapping from container name to list of port, subdomain pairs to expose to an HTTP proxy"

    @staticmethod
    def fetch(challenge_id: str, team_id: str) -> Challenge:
        """Fetches the appropriate Challenge instance given challenge ID and team ID."""
        return SharedChallenge(challenge_id)

    @abstractmethod
    def expiration(self) -> int | None:
        """Returns the expiration time of a challenge in seconds, or None if it isn't running."""
        pass

    @abstractmethod
    def start(self):
        """Starts a challenge, or renews it if it was already running."""
        pass

    @abstractmethod
    def stop(self):
        """Stops a challenge if it's running."""
        pass


class SharedChallenge(Challenge):
    """A challenge with one shared instance among all teams."""

    def __init__(self, id: str):
        """Constructs a SharedChallenge given the challenge ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id
        self.lifetime = 3600

    def start(self):
        namespace = f"cyber-instancer-{self.id}"

        api = client.AppsV1Api()
        capi = client.CoreV1Api()
        crdapi = client.CustomObjectsApi()

        curtime = int(time())
        expiration = curtime + self.lifetime

        with Lock(namespace):
            try:
                curns = capi.read_namespace(namespace)
                print(f"[*] Renewing namespace {namespace}...")
                curns.metadata.annotations[
                    "instancer.acmcyber.com/chall-expires"
                ] = str(expiration)
                capi.replace_namespace(namespace, curns)
                return
            except ApiException as e:
                if e.status != 404:
                    raise e
                print(f"[*] Making namespace {namespace}...")
                capi.create_namespace(
                    client.V1Namespace(
                        metadata=client.V1ObjectMeta(
                            name=namespace,
                            annotations={
                                "instancer.acmcyber.com/chall-expires": str(expiration)
                            },
                        )
                    )
                )

            for depname, container in self.containers.items():
                print(f"[*] Making deployment {depname} under namespace {namespace}...")
                dep = client.V1Deployment(
                    metadata=client.V1ObjectMeta(
                        name=depname,
                        labels={"instancer.acmcyber.com/instance-id": self.id},
                    ),
                    spec=client.V1DeploymentSpec(
                        selector=client.V1LabelSelector(
                            match_labels={"instancer.acmcyber.com/instance-id": self.id}
                        ),
                        replicas=1,
                        template=client.V1PodTemplateSpec(
                            metadata=client.V1ObjectMeta(
                                labels={"instancer.acmcyber.com/instance-id": self.id},
                                annotations={
                                    "instancer.acmcyber.com/chall-started": str(curtime)
                                },
                            ),
                            spec=client.V1PodSpec(
                                enable_service_links=False,
                                automount_service_account_token=False,
                                containers=[config_to_container(container)],
                            ),
                        ),
                    ),
                )
                api.create_namespaced_deployment(namespace, dep)

            for servname, container in self.containers.items():
                print(f"[*] Making service {servname} under namespace {namespace}...")
                exposed_ports = self.exposed_ports.get(servname, [])
                http_ports = self.http_ports.get(servname, [])
                if len(exposed_ports) > 0:
                    serv_spec = client.V1ServiceSpec(
                        selector={
                            "instancer.acmcyber.com/instance-id": self.id,
                        },
                        ports=[
                            client.V1ServicePort(port=port, target_port=port)
                            for port in exposed_ports
                        ],
                        type="NodePort",
                    )
                else:
                    serv_spec = client.V1ServiceSpec(
                        selector={
                            "instancer.acmcyber.com/instance-id": self.id,
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
                        labels={"instancer.acmcyber.com/instance-id": self.id},
                    ),
                    spec=serv_spec,
                )
                capi.create_namespaced_service(namespace, serv)

            for ingname, container in self.containers.items():
                http_ports = self.http_ports.get(ingname, [])
                if len(http_ports) > 0:
                    print(
                        f"[*] Making ingress {ingname} under namespace {namespace}..."
                    )
                    ing = {
                        "metadata": {"name": ingname},
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
                    crdapi.create_cluster_custom_object(
                        "traefik.containo.us",
                        "v1alpha1",
                        "ingressroutes",
                        ing,
                    )

    def stop(self):
        namespace = f"cyber-instancer-{self.id}"
        capi = client.CoreV1Api()

        print(f"[*] Deleting namespace {namespace}...")
        try:
            capi.delete_namespace(namespace)
        except ApiException as e:
            print(f"[*] Could not delete namespace {namespace}...")


class PerTeamChallenge(Challenge):
    """A challenge that needs to spawn a unique instance per team."""

    team_id: str

    def __init__(self, id: str, team_id: str):
        """Constructs a PerTeamChallenge given the challenge ID and team ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id
        self.team_id = team_id
