#!/bin/bash

# Run container registry server
docker rm --force -v registry
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Update fixture.sql to use our local docker registry and fake domain
sed -i 's/docker.acmcyber.com/192.168.0.10/g' /tmp/fixture.sql
sed -i 's/instancer.acmcyber.com/instancer.local/g' /tmp/fixture.sql

# Run postgres server
docker rm -f -v db
docker run -d -p 5432:5432 --restart=always --name db \
  -e POSTGRES_PASSWORD=wLLaHYLzrV3j4yL7ErPkmhzf -e POSTGRES_USER=instancer \
  -e POSTGRES_DB=instancer -v /tmp/fixture.sql:/docker-entrypoint-initdb.d/fixture.sql:ro postgres

# Allow insure docker pushes to own repo
cat << EOF > /etc/docker/daemon.json
{
  "insecure-registries" : ["http://192.168.0.10:5000"]
}
EOF

# Restart docker
systemctl restart docker

# Build instancer docker container
docker build /tmp/cyber-instancer/ -t 192.168.0.10:5000/cyber-instancer

# Push to registry
docker push 192.168.0.10:5000/cyber-instancer

# Build and push example challenge docker image
docker build /tmp/cyber-instancer/examples/simple-redis-chall -t 192.168.0.10:5000/simple-redis-chall
docker push 192.168.0.10:5000/simple-redis-chall

# Build and push queue-up challenge
docker build /tmp/cyber-instancer/examples/queue-up/queue -t 192.168.0.10:5000/queue-up-queue
docker push 192.168.0.10:5000/queue-up-queue
docker build /tmp/cyber-instancer/examples/queue-up/flagserver -t 192.168.0.10:5000/queue-up-flag
docker push 192.168.0.10:5000/queue-up-flag

# install k3
curl -sfL https://get.k3s.io | sh -

# restart cyber-instancer if it exists
kubectl rollout restart -n cyber-instancer deployment cyber-instancer

# allow k3 unauthenticated docker pulls
cat <<EOF >/etc/rancher/k3s/registries.yaml
mirrors:
  192.168.0.10:
    endpoint:
      - "http://192.168.0.10:5000"
EOF

systemctl restart k3s

# Install all of the instancer config files
kubectl apply -f - <<EOF
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
EOF

kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: instancer-config
  namespace: cyber-instancer
type: Opaque
stringData:
  config: |-
    secret_key: abcd
    login_secret_key: "+jRCqBlpa4Mqo558EVWfioZAIfiFEHgQvN6BxD7qBgQ="
    admin_team_id: 4b45bb80-9a8b-47ca-ad0d-a995b1ffe6d6
    redis:
      host: redis-service
    postgres:
      host: 192.168.0.10
      port: 5432
      user: instancer
      password: wLLaHYLzrV3j4yL7ErPkmhzf
      database: instancer
    in_cluster: true
    redis_resync_interval: 60
    dev: false
    url: "http://192.168.0.10"
    challenge_host: 192.168.0.10

EOF

kubectl apply -f - <<EOF
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
          image: 192.168.0.10/cyber-instancer:latest
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
          image: 192.168.0.10/cyber-instancer:latest
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
EOF

echo "Waiting 40 seconds..."
sleep 20
systemctl restart k3s
sleep 20

kubectl apply -f - <<EOF
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: cyber-instancer-ingress-ip
  namespace: cyber-instancer
spec:
  entryPoints:
    - web
    - websecure
  routes:
    - match: Host("192.168.0.10")
      kind: Rule
      services:
        - name: cyber-instancer-service
          port: 8080
---
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: cyber-instancer-ingress-fakedomain
  namespace: cyber-instancer
spec:
  entryPoints:
    - web
    - websecure
  routes:
    - match: Host("instancer.local")
      kind: Rule
      services:
        - name: cyber-instancer-service
          port: 8080
EOF
