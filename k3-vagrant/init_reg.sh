#!/bin/bash

# Run container registry server
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Update fixture.sql to use our local docker registry and fake domain
sed -i 's/docker.acmcyber.com/192.168.0.20/g' /tmp/fixture.sql
sed -i 's/egg.gnk.sh/instancer.local/g' /tmp/fixture.sql

# Run postgres server
docker run -d -p 5432:5432 --restart=always --name db \
  -e POSTGRES_PASSWORD=wLLaHYLzrV3j4yL7ErPkmhzf -e POSTGRES_USER=instancer \
  -e POSTGRES_DB=instancer -v /tmp/fixture.sql:/docker-entrypoint-initdb.d/fixture.sql:ro postgres

# Allow insure docker pushes to own repo
cat << EOF > /etc/docker/daemon.json
{
  "insecure-registries" : ["http://192.168.0.20:5000"]
}
EOF

# Restart docker
systemctl restart docker

# Build instancer docker container
docker build /tmp/cyber-instancer/ -t 192.168.0.20:5000/cyber-instancer

# Push to registry
docker push 192.168.0.20:5000/cyber-instancer

# Build and push example challenge docker image
docker build /tmp/cyber-instancer/examples/simple-redis-chall -t 192.168.0.20:5000/simple-redis-chall
docker push 192.168.0.20:5000/simple-redis-chall
