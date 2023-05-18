CREATE TABLE IF NOT EXISTS challenges(id varchar(256), name varchar(256), description text, author text, cfg json, per_team boolean, lifetime integer);
CREATE TABLE IF NOT EXISTS tags(challenge_id varchar(256), name varchar(64), is_category boolean);

COPY challenges (id, name, description, cfg, per_team, lifetime, author) FROM stdin;
per-team-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing2.egg.gnk.sh"]]}}	t	3600	aplet123
simple-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing.egg.gnk.sh"]]}}	f	3600	kaiphat
\.

COPY tags (challenge_id, name, is_category) FROM stdin;
simple-redis-chall	web	t
simple-redis-chall	cringe	f
simple-redis-chall	foobar	f
per-team-redis-chall	pwn	t
per-team-redis-chall	aplet123	f
\.
