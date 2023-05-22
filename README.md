# cyber-instancer

Challenge Instancer Project for 35L. Please do not touch unless you are part of the PeanutButteR S23 35L group.

# Setup

Please note: setup for this application is done in 3 stages: deploying a kubernetes cluster, setting up a docker container repository, and (finally) actually deploying this app into the kubernetes cluster.

## Requirements:

- A kubernetes cluster. For this project (and this setup tutorial), we will be using [k3s](https://k3s.io/) deployed on a linux box, so [the minimum k3s requirement](https://docs.k3s.io/installation/requirements) must be met:
  - An x86_64 linux machine with preferably minimum 4GB ram
    - Nothing other than the bare minimum in services (ssh) should be running. k3s requires a lot of ports, including 80, 443, 6443, and all ports 30000-32767
    - All ports should be accessible from the internet
    - Our guide assumes you are using ubuntu or a similar linux system, but should work on any standard linux distribution that k3s supports
- A (sub)domain to point towards the application, including a wildcard subdomain for challenge urls. Ideally the DNS provider should have an API that's supported by cert-manager for easy certificate autoprovisioning.
- A Docker registry. For this setup tutorial we will be self-hosting an unauthenticated Docker registry. Ideally the Docker registry should be on a domain which you can obtain an HTTPS certificate for. This tutorial will be using Cloudflare.
- A postgres server. For this setup tutorial we will also be self-hosting it using Docker.
- [docker](https://docs.docker.com/get-docker/), [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Config files

- `backend/config.yml`: copy `config.example.yml` and fill with credentials to redis and postgres. If using docker compose development environment, set

```yaml
redis:
  host: redis-service
```

- `login_secret_key` can be created by running the following in a python3 interpreter:

```python
import base64
import secrets
base64.b64encode(secrets.token_bytes(32))
```

Do NOT share this, or else an attacker will be able to login as whomever they wish!

- `k3s.yaml`: If running this app outside of the kubernetes cluster, copy kubernetes authentication config into this file. For k3s, this file can be found at `/etc/rancher/k3s/k3s.yaml`, and modify `clusters[0].cluster.server` or similar to be the actual remote ip address and not `127.0.0.1`.

## Kubernetes Setup

- Install the [Traefik Ingress Controller](https://doc.traefik.io/traefik/providers/kubernetes-ingress/) on your cluster. If using k3s, it'll already be installed and you don't have to do anything.
- Install [cert-manager](https://cert-manager.io) on your cluster.
- Create a `Secret` with a Cloudflare API token that has permission to edit zone DNS for the domain you want to put challenges on:

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

```sql
CREATE TABLE public.challenges (
    id character varying(256) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    cfg json NOT NULL,
    per_team boolean NOT NULL,
    lifetime integer NOT NULL,
    author text NOT NULL,
    CONSTRAINT challenges_lifetime_check CHECK ((lifetime >= 0))
);
CREATE TABLE public.tags (
    challenge_id character varying(256) NOT NULL,
    name character varying(64) NOT NULL,
    is_category boolean NOT NULL
);

ALTER TABLE ONLY public.challenges
    ADD CONSTRAINT challenges_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (challenge_id, name);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_challenge_id_fkey FOREIGN KEY (challenge_id) REFERENCES public.challenges(id);
```

# Available Development Commands

## Root Project directory

Runs app in a development enviornment. Requires [Docker Compose](https://docs.docker.com/compose/install/) (and by extension docker) to be installed.

- `docker compose up --build -d` (same as `npm run dev`): (re)starts images, rebuilding react and running flask server on port 8080
- `docker compose down`: Stops flask server

## Inside Frontend directory

### `npm run build`

Builds the app for production to the `build` folder.
It bundles React in production mode and optimizes the build for the best performance.

### `npm run dev`

Same as running `docker compose up --build -d` in project root: see above

### `npm run lint`

Test linter against code to ensure code conformity.

### `npm run preview`

Builds just the react app and runs a preview. Does not startup any backend server and will probably be non-functional.
