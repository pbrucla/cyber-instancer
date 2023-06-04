# cyber-instancer

Challenge Instancer Project for 35L. Please do not touch unless you are part of the PeanutButteR S23 35L group.

# Setup

Please note: setup for this application is done in 3 stages: deploying a kubernetes cluster, setting up a docker container repository, and (finally) actually deploying this app into the kubernetes cluster.

There are essentially 3 ways to run this application.

- Production: Run the kubernetes cluster on a remote server, which will contain redis and the instancer application itself, with a separate Postgres and docker container registry service hosted locally or on another machine
  - See the "[Requirements](#requirements)", "[Config files](#config-files)", "[Kubernetes setup](#kubernetes-setup)", and "[Database setup](#database-setup)" sections below
- Partially Local: Run the kubernetes cluster on a remote server, but the cyber instancer, redis, and postgres services will run locally. This is the easiest way to run a full application without requiring large amounts of configuration for each user if a kubernetes cluster is already setup. This option also allows for subdomain provisioning to work properly.
  - simply setup `config.yml`, `k3s.yaml`, and then use docker compose
  - See the "[Requirements](#requirements)", "[Config files](#config-files)", "[Kubernetes setup](#kubernetes-setup)", and "[Docker Compose](#docker-compose)" sections below
- Fully Local: Run everything locally. This can be done manually or by using the provided Vagrantfile.
  - This setup does not support https and will require manual /etc/hosts editing or similar for (sub)domains to access instancer
  - See "Config files" and "Vagrant" sections below

## Requirements:

- A kubernetes cluster. For this project (and this setup tutorial), we will be using [k3s](https://k3s.io/) deployed on a linux box, so [the minimum k3s requirement](https://docs.k3s.io/installation/requirements) must be met:
  - An x86_64 cloud linux machine or virtual machine with preferably minimum 4GB ram
    - Nothing other than the bare minimum in services (ssh) should be running. k3s requires a lot of ports, including 80, 443, 6443, and all ports 30000-32767
    - All ports should be accessible from wherever users may be connectinf from
- A (sub)domain to point towards the application, including a wildcard subdomain for challenge urls. Ideally the DNS provider should have an API that's supported by cert-manager for easy certificate autoprovisioning.
- A Docker registry. For this setup tutorial we will be self-hosting an unauthenticated Docker registry. Ideally the Docker registry should be on a domain which you can obtain an HTTPS certificate for. This tutorial will be using Cloudflare.
- A postgres server. For this setup tutorial we will also be self-hosting it using Docker.
- [docker](https://docs.docker.com/get-docker/), [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Config files

### config.yml

Copy `config.example.yml` to `config.yml` and update with your information. See below for more info:

- `login_secret_key` can be created by running the following in a python3 interpreter:

```python
import base64
import secrets
base64.b64encode(secrets.token_bytes(32))
```

Do NOT share this, or else an attacker will be able to login as whomever they wish!

- `admin_team_id`: UUID of admin account. Decode a login token to get an account's UUID, and then set the UUID here.
- `redis`: connection information for redis. If using the kubernetes config files below, docker compose, or vagrant, set `host: redis-service` and delete the port and password options. If you have a separate redis host, set that here.
- `postgres`: connection information for postgres. If using docker-compose, make sure the host is `db`, and that the username, password, and database name match the corresponding config options in `docker-compose.yml`
- `in_cluster`: set if it will be deployed in a cluster. If not, will use a `k3s.yaml` file at the top level directory to authenticate with cluster.
- `redis_resync_interval`: How often to sync between active clusters and the local cache, deleting instances as necessary.
- `dev`: Enables some developer debugging api endpoints. Do not enable in production.
- `url`: URL to the instancer.
- `challenge_host`: IP or hostname that points to the kube cluster. Usually same as `url` but without http(s)

### k3s.yaml

- If running this app outside of the kubernetes cluster, copy kubernetes authentication config into this file. For k3s, this file can be found at `/etc/rancher/k3s/k3s.yaml`, and modify `clusters[0].cluster.server` or similar to be the actual remote ip address and not `127.0.0.1`.

## Kubernetes Setup

- Install the [Traefik Ingress Controller](https://doc.traefik.io/traefik/providers/kubernetes-ingress/) on your cluster. If using k3s, it'll already be installed and you don't have to do anything.
- Install [cert-manager](https://cert-manager.io) on your cluster.

### kubectl config files

- Each of the following files can be applied using `sudo kubectl` by running `kubectl apply -f PATH/TO/FILE` on the machine with k3s installed, or like `kubectl apply -f -` to read from stdin.
- Create a `Secret` with a [Cloudflare API token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/) that has permission to edit zone DNS for the domain you want to put challenges on:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cloudflare-token
type: Opaque
stringData:
  api-token: "TOKEN-GOES-HERE"
```

- Create a cert-manager `Issuer` to solve ACME dns01 challenges using the secret:

```yaml
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: letsencrypt-issuer
spec:
  acme:
    email: "EMAIL@GOES.HERE"
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: letsencrypt-issuer-key
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: cloudflare-token
              key: api-token
```

Note that cloudflare on its free plan does NOT offer certificates for `*.subdomain.domain.tld`, so you will need to disable cloudflare's reverse proxy for at least sub-subdomains.

- Create a cert-manager `Certificate` using the issuer:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: wildcard-domain
spec:
  secretName: wildcard-domain
  issuerRef:
    name: letsencrypt-issuer
    kind: Issuer
    group: cert-manager.io
  commonName: "*.DOMAIN.GOES.HERE"
  dnsNames:
    - "DOMAIN.GOES.HERE"
    - "*.DOMAIN.GOES.HERE"
```

- Create a traefik `TLSStore` using the certificate:

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: TLSStore
metadata:
  name: default
spec:
  certificates:
    - secretName: wildcard-domain
  defaultCertificate:
    secretName: wildcard-domain
```

- If running the instancer on the cluster (recommended), create a namespace for it, a service account, a cluster role for the service account, and a cluster role binding to bind the role to the service account:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  labels:
    kubernetes.io/metadata.name: cyber-instancer
  name: cyber-instancer
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cyber-instancer
  namespace: cyber-instancer
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cyber-instancer
  namespace: cyber-instancer
rules:
  - apiGroups: [""]
    resources: ["services", "namespaces"]
    verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["networking.k8s.io"]
    resources: ["ingresses", "networkpolicies"]
    verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
  - apiGroups: ["traefik.containo.us"]
    resources: ["ingressroutes"]
    verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cyber-instancer-binding
  namespace: cyber-instancer
subjects:
  - kind: ServiceAccount
    name: cyber-instancer
    namespace: cyber-instancer
roleRef:
  kind: ClusterRole
  name: cyber-instancer
  apiGroup: rbac.authorization.k8s.io
```

- Create a secret with the config file contents that can be mounted into the image:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: instancer-config
  namespace: cyber-instancer
type: Opaque
stringData:
  config: |-
    secret_key: asdf
    foo: bar
```

- Create a deployment for the instancer, a service for that deployment, and a Traefik ingress route for that service (a normal Kubernetes ingress works too), as well as a deployment for the worker, a deployment for redis, and a service for that deployment (make sure to edit `YOUR_DOCKER_REGISTRY` and `YOUR_DOMAIN` accordingly, keeping in mind that the domain has to match the certificate domain in order for https to work properly):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cyber-instancer
  namespace: cyber-instancer
  labels:
    app.kubernetes.io/name: cyber-instancer
spec:
  replicas: 4
  selector:
    matchLabels:
      app.kubernetes.io/name: cyber-instancer
  template:
    metadata:
      labels:
        app.kubernetes.io/name: cyber-instancer
    spec:
      serviceAccountName: cyber-instancer
      containers:
        - name: app
          image: YOUR_DOCKER_REGISTRY/cyber-instancer:latest
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: 500m
              memory: 512Mi
            requests:
              cpu: 50m
              memory: 64Mi
          volumeMounts:
            - name: config
              mountPath: "/app/config.yml"
              readOnly: true
              subPath: "config.yml"
      volumes:
        - name: config
          secret:
            secretName: instancer-config
            items:
              - key: config
                path: config.yml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: cyber-instancer
  labels:
    app.kubernetes.io/name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: redis
  template:
    metadata:
      labels:
        app.kubernetes.io/name: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            limits:
              cpu: 500m
              memory: 512Mi
            requests:
              cpu: 50m
              memory: 64Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cyber-instancer-worker
  namespace: cyber-instancer
  labels:
    app.kubernetes.io/name: cyber-instancer-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: cyber-instancer-worker
  template:
    metadata:
      labels:
        app.kubernetes.io/name: cyber-instancer-worker
    spec:
      serviceAccountName: cyber-instancer
      containers:
        - name: app
          image: YOUR_DOCKER_REGISTRY/cyber-instancer:latest
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: 500m
              memory: 512Mi
            requests:
              cpu: 50m
              memory: 64Mi
          command: ["python", "worker.py"]
          volumeMounts:
            - name: config
              mountPath: "/app/config.yml"
              readOnly: true
              subPath: "config.yml"
      volumes:
        - name: config
          secret:
            secretName: instancer-config
            items:
              - key: config
                path: config.yml
---
apiVersion: v1
kind: Service
metadata:
  name: cyber-instancer-service
  namespace: cyber-instancer
  labels:
    app.kubernetes.io/name: cyber-instancer-service
spec:
  selector:
    app.kubernetes.io/name: cyber-instancer
  type: NodePort
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
      nodePort: 31337
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: cyber-instancer
  labels:
    app.kubernetes.io/name: redis-service
spec:
  selector:
    app.kubernetes.io/name: redis
  ports:
    - protocol: TCP
      port: 6379
---
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: cyber-instancer-ingress
  namespace: cyber-instancer
spec:
  entryPoints:
    - web
    - websecure
  routes:
    - match: Host(`YOUR_DOMAIN`)
      kind: Rule
      services:
        - name: cyber-instancer-service
          port: 8080
```

## Database Setup

Create a table for the database:

- copy-paste and run all of the commands in `fixture.sql`, replacing the domains with your own. If using docker compose, on first run, docker compose will automatically build the database.

# Available Development Commands

## Formatting

In this repository, we are using many different linters to help format all of the different types of code involved in the project. To install the checks, [install pre-commit](https://pre-commit.com/#installation), and then run `pre-commit install`. Now, pre-commit will run on all staged files, and will stop you from making a commit that fails a check. Note that after pre-commit fails in a commit, it will format the files properly, but you still need to `git add` those changes.

## Docker Compose

Runs app in a development enviornment. Requires [Docker Compose](https://docs.docker.com/compose/install/) (and by extension docker) to be installed.

- `docker compose up --build -d` (same as `npm run dev`): (re)starts images, rebuilding react and running flask server on port 8080
- `docker compose down`: Stops flask server

## Vagrant

Vagrant is a program that allows for automatic virtual machine deployment. It itself does NOT run virtual machines; rather, it will hook into other software such as VMWare Workstation, Hyper-V, or VirtualBox to run the machines.

### Requirements

- A machine with resources to run a virtual machine. Recommended at least 12GB RAM and 6 CPU threads locally - the default VM settings is 8GB ram and 4 CPU threads.
- `vagrant` must be installed and setup, including a compatible virtualization software.
  1. Download and install vagrant from <https://developer.hashicorp.com/vagrant/downloads>.
  2. Download and install [virtualbox (windows/linux)](https://www.virtualbox.org/wiki/Downloads) or [VMware Fusion (macos, intel or m1)](https://customerconnect.vmware.com/en/evalcenter?p=fusion-player-personal-13):
  - For VMWare Fusion, please follow the instructions under "Installation" here after install VMWare Fusion: <https://developer.hashicorp.com/vagrant/docs/providers/vmware/installation>.
  - For virtualbox, replace all instances of "192.168.0" with "192.168.56". On linux, you can do this with `sed -i "s/192.168.0/192.168.56/g" *`
  - [For windows, you may need to disable/enable some settings to get virtualbox to work](https://superuser.com/questions/1391838/virtual-box-is-not-working-on-windows-10)
- `rsync` must be installed. One way to do so on windows is install it via [Cygwin](https://www.cygwin.com/install.html) and select both `rsync` and `ssh`, and on macos, use [homebrew](https://brew.sh) with `brew install rsync`.

### Running

- Update `is_arm64` in `k3-vagrant/Vagrantfile`: set this to `return true` if you are on an m1/m2 mac, `return false` if on x86_64 (basically everything else).
- In a terminal window, change to the `k3-vagrant` directory, then run `vagrant up`. You may need to use `--provider=virtualbox` or `--provider=vmware_desktop` if vagrant chooses the wrong virtualization software - run `vagrant destroy` if it gives an error about already deployed vms. This may take a while depending on your system. Note that some of the command's repsonse may be be red - this is normal.
- Occasionally, provisioning may fail with something along the lines of "The SSH command responded with a non-zero exit status." In this case, run `vagrant provision`.
- `vagrant suspend` will suspend the vms, allowing for safe resuming, `vagrant halt` will fully shutdown the vms (unsupported).
- Once you are done, `vagrant destroy` will delete the vms.

### Accessing the instancer

- You can access the instancer at `192.168.0.10` (vmware), or `192.168.56.10` (virtualbox).
- In order to access the instancer's web deployments, you must either fake your hosts header or add the challenges to your `/etc/hosts` file:
  - Fake hosts: use an extension such as <https://addons.mozilla.org/en-US/firefox/addon/vhost-simulator/>, and add both the IP above and the host you are trying to access, like `testing.instancer.local`. Adding `instancer.local` pointing to the above IP will allow for accessing the instancer website.
  - Add to `/etc/hosts`: Add to the bottom of `/etc/hosts` following the below format:

```
192.168.0.10  instancer.local
192.168.0.10  testing.instancer.local
192.168.0.10  testing2.instancer.local
...
```

- Adjust the IP addresses as required. Note that some browsers may ignore `/etc/hosts`, and you may need to disable secure DNS in order for the browser to use `/etc/hosts`.

## Inside Frontend directory

These commands are more or less legacy since the react app is heavily dependent on a backend existing. Nevertheless, they are still here.

### `npm run build`

Builds the app for production to the `build` folder.
It bundles React in production mode and optimizes the build for the best performance.

### `npm run dev`

Same as running `docker compose up --build -d` in project root: see above

### `npm run lint`

Test linter against code to ensure code conformity. Superceded by [pre-commit checks](https://pre-commit.com/#installation).

### `npm run preview`

Builds just the react app and runs a preview. Does not startup any backend server and will probably be non-functional.
