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

## Database Setup

Create a table for the database:

```sql
CREATE TABLE IF NOT EXISTS challenges(id varchar(256), name varchar(256), description text, lifetime integer, cfg json, per_team boolean);
```

# Available Development Commands
## Root Project directory

Runs app in a development enviornment. Requires [Docker Compose](https://docs.docker.com/compose/install/) (and by extension docker) to be installed.
- `docker compose up --build -d` (same as `npm run dev`): (re)starts images, rebuilding react and running flask server on port 8080
- `docker compose down`: Stops flask server

## Inside Backend directory

### `npm run build`

Builds the app for production to the `build` folder.
It bundles React in production mode and optimizes the build for the best performance.

### `npm run dev`

Same as running `docker compose up --build -d` in project root: see above

### `npm run lint`

Test linter against code to ensure code conformity.

### `npm run preview`

Builds just the react app and runs a preview. Does not startup any backend server and will probably be non-functional.
