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
CREATE TABLE public.teams (
    team_id UUID PRIMARY KEY,
    team_username text UNIQUE,
    team_email text UNIQUE
);

COPY challenges (id, name, description, cfg, per_team, lifetime, author) FROM stdin;
per-team-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing2.egg.gnk.sh"]]}}	t	3600	aplet123
simple-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing.egg.gnk.sh"]]}}	f	3600	kaiphat
private-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "http": {"app": [[8080, "testing3.egg.gnk.sh"]]}}	f	3600	kaiphat
\.

COPY tags (challenge_id, name, is_category) FROM stdin;
simple-redis-chall	web	t
simple-redis-chall	cringe	f
simple-redis-chall	foobar	f
per-team-redis-chall	pwn	t
per-team-redis-chall	aplet123	f
private-redis-chall	rev	t
private-redis-chall	private	f
\.

ALTER TABLE ONLY public.challenges
    ADD CONSTRAINT challenges_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (challenge_id, name);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_challenge_id_fkey FOREIGN KEY (challenge_id) REFERENCES public.challenges(id);
