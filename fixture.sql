CREATE TABLE public.challenges (
    id character varying(256) NOT NULL,
    name character varying(256) NOT NULL,
    description text NOT NULL,
    cfg json NOT NULL,
    per_team boolean NOT NULL,
    lifetime integer NOT NULL,
    boot_time integer NOT NULL,
    author text NOT NULL,
    CONSTRAINT challenges_lifetime_check CHECK ((lifetime > 0)),
    CONSTRAINT challenges_boot_time_check CHECK ((boot_time >= 0 AND boot_time < lifetime))
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

COPY challenges (id, name, description, cfg, per_team, lifetime, boot_time, author) FROM stdin;
per-team-redis-chall	Per Team Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing2.instancer.acmcyber.com"]]}}	t	3600	10	aplet123
simple-redis-chall	Simple Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing.instancer.acmcyber.com"]]}}	f	3600	10	kaiphat
private-redis-chall	Private Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "http": {"app": [[8080, "testing3.instancer.acmcyber.com"]]}}	f	3600	10	kaiphat
short-lived-redis-chall	Short Lived Redis Chall	This is a testing challenge for the instancer.	{"containers": {"app": {"image": "docker.acmcyber.com/simple-redis-chall:latest", "ports": [8080]}, "redis": {"image": "redis:7-alpine", "ports": [6379]}}, "tcp": {"redis": [6379]}, "http": {"app": [[8080, "testing4.instancer.acmcyber.com"]]}}	t	120	15	winning
lactf-2023-queue-up	Queue Up!	This is a challenge from LA CTF 2023 titled Queue Up!	{"containers":{"queue":{"image":"docker.acmcyber.com/queue-up-queue:latest","ports":[8080],"environment":{"PORT":"8080","startTime":"1674372589","POSTGRES_USER":"queue","POSTGRES_PASSWORD":"BnA6tObcPm44I7RMb1Xqajs5UYl5LWsMMC4BYpHwoPp6jc7Tk4","FLAG_SERVER_URL":"https://qu-flag.instancer.acmcyber.com","ADMIN_SECRET":"0wN7Q3JQC9Ae4Q9M1kXaserN5byNmvMjHDSsvmjvvh2gYUeBfZnTUNlo"}},"db":{"image":"postgres","environment":{"POSTGRES_USER":"queue","POSTGRES_PASSWORD":"BnA6tObcPm44I7RMb1Xqajs5UYl5LWsMMC4BYpHwoPp6jc7Tk4"},"ports":[5432]},"flagserver":{"image":"docker.acmcyber.com/queue-up-flag:latest","ports":[3000],"environment":{"QUEUE_SERVER_URL":"https://qu-queue.instancer.acmcyber.com","QUEUE_SERVER_PORT":"8080","FLAG":"lactf{Byp455in_7he_Qu3u3}","PORT":"3000","ADMIN_SECRET":"0wN7Q3JQC9Ae4Q9M1kXaserN5byNmvMjHDSsvmjvvh2gYUeBfZnTUNlo"}}},"http":{"queue":[[8080,"qu-queue.instancer.acmcyber.com"]],"flagserver":[[3000,"qu-flag.instancer.acmcyber.com"]]}}	f	3600	30	burturt
baby-sqli	Baby SQLI	Hey look it's a site that uses unescaped SQL surely this can't go wrong right???	{"containers": {"app": {"image": "docker.acmcyber.com/baby-sqli:latest", "ports": [8080]}}, "http": {"app": [[8080, "baby-sqli.instancer.acmcyber.com"]]}}	t	120	10	aplet123
\.

COPY tags (challenge_id, name, is_category) FROM stdin;
simple-redis-chall	web	t
simple-redis-chall	cringe	f
simple-redis-chall	foobar	f
per-team-redis-chall	pwn	t
per-team-redis-chall	aplet123	f
private-redis-chall	rev	t
private-redis-chall	private	f
short-lived-redis-chall	crypto	t
short-lived-redis-chall	quick	f
lactf-2023-queue-up	web	t
lactf-2023-queue-up	medium	f
lactf-2023-queue-up	lactf	f
baby-sqli	web	t
baby-sqli	easy	f
\.

ALTER TABLE ONLY public.challenges
    ADD CONSTRAINT challenges_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (challenge_id, name);

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_challenge_id_fkey FOREIGN KEY (challenge_id) REFERENCES public.challenges(id);
