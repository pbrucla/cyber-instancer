from __future__ import annotations
from abc import ABC, abstractmethod
from kubernetes import client, config as kconfig
from kubernetes.client.exceptions import ApiException
from config import config, rclient
from time import time
from typing import Any

if config.in_cluster:
    kconfig.load_incluster_config()
else:
    kconfig.load_kube_config()


def snake_to_camel(snake: str):
    return "".join(x.capitalize() for x in snake.split("_"))


def config_to_container(cfg: dict):
    cont_name = cfg["name"]
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
        if prop in kube:
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
    containers: list[dict]
    "List of challenge container configs."
    exposed_ports: list[int]
    "List of container ports to expose"
    http_ports: list[int]
    "List of ports to expose to an HTTP proxy"

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
        """Starts a challenge, or restarts it if it was already running."""
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
        depname = f"cyber-instancer-{self.id}-dep"
        servname = f"cyber-instancer-{self.id}-svc"
        ingname = f"cyber-instancer-{self.id}-ing"

        api = client.AppsV1Api()
        capi = client.CoreV1Api()
        napi = client.NetworkingV1Api()

        curtime = int(time())
        expiration = curtime + self.lifetime

        print(f"[*] Making namespace {namespace}...")
        try:
            capi.read_namespace(namespace)
        except ApiException as e:
            if e.status != 404:
                raise e
            print(f"[*] Namespace doesn't exist, creating for first time...")
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
        print(f"[*] Making deployment {depname} under namespace {namespace}...")
        dep = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=depname, labels={"instancer.acmcyber.com/instance-id": self.id}
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
                        containers=[config_to_container(x) for x in self.containers],
                    ),
                ),
            ),
        )
        try:
            print("[*] Attempting to patch deployment...")
            curdep = api.read_namespaced_deployment(depname, namespace)
            dep.metadata.resource_version = curdep.metadata.resource_version
            api.replace_namespaced_deployment(depname, namespace, dep)
        except ApiException as e:
            if e.status == 404:
                print("[*] Deployment doesn't exist, creating for first time...")
                api.create_namespaced_deployment(namespace, dep)
            else:
                raise e
        print(f"[*] Making service {servname} under namespace {namespace}...")
        if len(self.exposed_ports) > 0:
            serv_spec = client.V1ServiceSpec(
                selector={
                    "instancer.acmcyber.com/instance-id": self.id,
                },
                ports=[
                    client.V1ServicePort(port=port, target_port=port)
                    for port in self.exposed_ports
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
                    for port in self.http_ports
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
        try:
            print("[*] Attempting to patch service...")
            curserv = capi.read_namespaced_service(servname, namespace)
            serv.metadata.resource_version = curserv.metadata.resource_version
            capi.replace_namespaced_service(servname, namespace, serv)
        except ApiException as e:
            if e.status == 404:
                print("[*] Service doesn't exist, creating for first time...")
                capi.create_namespaced_service(namespace, serv)
            else:
                raise e
        # if len(chall.get("http", [])) > 0:
        #     print(f"[*] Making ingress {ingname} under namespace {namespace}...")
        #     ing = client.V1Ingress(
        #         metadata=client.V1ObjectMeta(
        #             name=ingname,
        #             annotations={"cert-manager.io/cluster-issuer": "letsencrypt"},
        #         ),
        #         spec=client.V1IngressSpec(
        #             ingress_class_name="nginx",
        #             tls=[
        #                 client.V1IngressTLS(
        #                     hosts=[
        #                         x["subdomain"] + settings.ingress_suffix
        #                         for x in chall["http"]
        #                     ],
        #                     secret_name=chall["name"],
        #                 )
        #             ],
        #             rules=[
        #                 client.V1IngressRule(
        #                     host=x["subdomain"] + settings.ingress_suffix,
        #                     http=client.V1HTTPIngressRuleValue(
        #                         paths=[
        #                             client.V1HTTPIngressPath(
        #                                 path="/",
        #                                 path_type="Prefix",
        #                                 backend=client.V1IngressBackend(
        #                                     service=client.V1IngressServiceBackend(
        #                                         name=servname,
        #                                         port=client.V1ServiceBackendPort(
        #                                             number=x["port"]
        #                                         ),
        #                                     )
        #                                 ),
        #                             )
        #                         ]
        #                     ),
        #                 )
        #                 for x in chall["http"]
        #             ],
        #         ),
        #     )
        #     try:
        #         print("[*] Attempting to patch ingress...")
        #         curing = napi.read_namespaced_ingress(ingname, namespace)
        #         ing.metadata.resource_version = curing.metadata.resource_version
        #         napi.replace_namespaced_ingress(ingname, namespace, ing)
        #     except ApiException as e:
        #         if e.status == 404:
        #             print("[*] Ingress doesn't exist, creating for first time...")
        #             napi.create_namespaced_ingress(namespace, ing)
        #         else:
        #             raise e
        # else:
        #     print("[*] Ensuring unused ingress has been removed...")
        #     removed = False
        #     try:
        #         curing = napi.read_namespaced_ingress(ingname, namespace)
        #     except ApiException as e:
        #         if e.status == 404:
        #             removed = True
        #             print("[*] Ingress doesn't exist, no action needed...")
        #         else:
        #             raise e
        #     if not removed:
        #         print("[*] Found unused ingress, deleting...")
        #         napi.delete_namespaced_ingress(ingname, namespace)

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
