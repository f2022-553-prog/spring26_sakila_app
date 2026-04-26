# Part D: Reflection & Architecture Documentation
**Student:** Abtaha | **Roll:** f2022-553 | **Section:** Spring 2026  
**Assignment:** DevOps & Cloud Computing Fundamentals — Sakila Flask App Pipeline

---

## D1: Architecture Diagrams

### Diagram 1 — Docker Compose Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HOST MACHINE                                  │
│                                                                     │
│  :5000 ──────► ┌─────────────┐    ┌─────────────┐ ◄── :8080        │
│                │   app       │    │  db-admin   │                   │
│                │ (Flask)     │    │  (Adminer)  │                   │
│                │             │    │             │                   │
│                │ ENV:        │    │ depends_on: │                   │
│                │ MYSQL_HOST= │    │   db        │                   │
│                │   db        │    └──────┬──────┘                   │
│                │ depends_on: │           │                          │
│                │   db        │           │                          │
│                │ (healthy)   │           │                          │
│                └──────┬──────┘           │                          │
│                       │                  │                          │
│            ┌──────────▼──────────────────▼──────┐                  │
│            │         sakila-network              │                  │
│            │         (bridge, custom)            │                  │
│            │                                     │                  │
│            │  ┌─────────────────────────────┐    │                  │
│            │  │           db                │    │                  │
│            │  │       (MySQL 8.0)           │    │                  │
│            │  │                             │    │                  │
│            │  │  ENV: MYSQL_ROOT_PASSWORD   │    │                  │
│            │  │       MYSQL_DATABASE        │    │                  │
│            │  │  healthcheck: mysqladmin    │    │                  │
│            │  │  restart: unless-stopped    │    │                  │
│            │  │  mem_limit: 512m            │    │                  │
│            │  └──────────────┬──────────────┘    │                  │
│            └─────────────────┼───────────────────┘                  │
│                              │ volume mount                         │
│                    ┌─────────▼──────────┐                           │
│                    │  sakila-db-data    │                           │
│                    │  (named volume)    │                           │
│                    └────────────────────┘                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  test-runner (profile: test — only runs with --profile test) │   │
│  │  CMD: python -m pytest tests/ -v                             │   │
│  │  depends_on: db (healthy) | same network                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

.env file ──► (MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, etc.)
             injected into db and app services at runtime
```

### Diagram 2 — CI/CD Pipeline Stages

```
  PUSH/PR EVENT
       │
       ▼
  ┌──────────┐
  │  lint    │  ← runs on: push (main/develop), pull_request
  │ (flake8) │    fails fast if code style errors found
  └────┬─────┘
       │ needs: lint
       ▼
  ┌──────────┐
  │  test    │  ← MySQL service container spun up automatically
  │ (pytest) │    Sakila DB imported, env vars set to 127.0.0.1
  └────┬─────┘
       │ needs: test
       ▼
  ┌──────────────────┐
  │  build           │  ← Docker image built, tagged with git SHA
  │  (docker build)  │    smoke test: curl localhost:5000
  └────┬─────────────┘
       │ needs: build
       ▼
  ┌──────────────────┐
  │  security-scan   │  ← Trivy scans image for CVEs
  │  (Trivy)         │    exit-code: 0  (never blocks pipeline)
  │                  │    report uploaded as artifact
  └──────────────────┘
       │
       │  (only on push to main — separate deploy.yml)
       ▼
  ┌─────────────────────┐
  │  deploy-staging     │  ← simulated staging deployment
  │  (auto)             │    writes Job Summary to GITHUB_STEP_SUMMARY
  └────────┬────────────┘
           │ needs: deploy-staging
           │ environment: production (manual approval gate)
           ▼
  ┌─────────────────────┐
  │  deploy-production  │  ← creates GitHub Release (vYYYY.MM.DD)
  │  (manual approval)  │    echoes simulated Slack notification
  └─────────────────────┘
```

---

## D2: Critical Reflection Report

### 1. Git Workflow Analysis

A branching strategy is essential in team environments because it creates clear ownership boundaries, prevents conflicting changes from colliding on the main codebase, and enables parallel development without instability. In this assignment, using `develop` as an integration branch and separate `feature/` branches meant that experimental changes were isolated until they were reviewed and proven stable. Without this, two developers modifying `config.py` simultaneously would have immediately broken each other's work. Regarding **merge vs. rebase**: `git merge` preserves the full history of how changes came together, including a dedicated merge commit — this is useful on shared branches like `develop` or `main` where transparency matters. `git rebase` rewrites commit history to appear linear, which is cleaner to read but rewrites SHAs and should never be used on public branches already shared with others. In this assignment, rebasing was appropriate when syncing with `upstream/main` locally (before pushing), because it replays our commits cleanly on top of upstream changes without cluttering history with unnecessary merge commits.

---

### 2. Docker Optimization Justification

The broken `Dockerfile.broken` had six key problems that were each addressed in the optimized version. First, using `python:3.9` as a base pulls a 900MB+ full Debian image; switching to `python:3.9-slim` or `python:3.9-alpine` cuts this to under 200MB, directly addressing the 40% size reduction requirement. Second, installing packages with three separate `RUN pip install` statements creates three unnecessary layers; consolidating them into one `RUN pip install -r requirements.txt` reduces layers and benefits from Docker's layer cache — if `requirements.txt` doesn't change, this layer is never rebuilt. Third, `COPY . /app` before installing dependencies invalidates the pip cache on every source code change; the correct order is to copy `requirements.txt` first, run `pip install`, then copy application code — this way, dependency installation is only re-run when requirements actually change. Fourth, hardcoding `MYSQL_PASSWORD=supersecretpassword` directly in the Dockerfile embeds secrets into the image and into version control history permanently — anyone with the image can extract them via `docker inspect`. Secrets must instead be passed at runtime via environment variables or Docker secrets. Fifth, exposing ports 3306 and 22 from a Flask application container is unnecessary and creates attack surface — only port 5000 should be exposed. Sixth, running the process as root inside the container means a container escape would immediately grant root access on the host; adding a non-root user (`adduser --disabled-password appuser`) and switching with `USER appuser` significantly reduces this risk. The `HEALTHCHECK` instruction was also added so Docker and Compose can determine when the application is genuinely ready to serve traffic, not just when the process started.

---

### 3. Networking Analysis

Docker's **default bridge network** (`docker0`) connects all containers on a single host but does not provide automatic DNS resolution between containers — they can only reach each other by IP address, which changes every restart. A **user-defined bridge network** (like `sakila-net` or `sakila-network` created in this assignment) enables Docker's embedded DNS server, which maps container names to their current IPs automatically. This is why `ping sakila-db` worked from inside the Flask container — Docker resolved `sakila-db` by name because both containers were on the same user-defined network. The DNS mechanism Docker uses is a lightweight internal resolver running at `127.0.0.11` inside each container; it intercepts name lookups and resolves them against the current list of containers on the same network. This is also why the cross-network isolation test succeeded: a container on `sakila-isolated` has no DNS entry for `sakila-db` on `sakila-net`, and the routing tables on the bridge interfaces are completely separate, so connectivity fails at both the DNS and IP routing levels.

---

### 4. Docker Compose vs. Manual Commands

Running the Sakila stack manually required remembering the correct network name, IP assignments, volume mounts, environment variables, dependency order, and port mappings for every container — across four services. Docker Compose solves this by encoding all of those decisions declaratively in a single `docker-compose.yml` file that is version-controlled, reproducible, and readable by any team member. It also handles startup ordering via `depends_on` with health conditions, which is extremely difficult to implement reliably with manual `docker run` commands. Regarding teardown: `docker compose down` stops and removes containers and networks, but leaves named volumes intact — the database data survives. `docker compose down -v` additionally removes all named volumes, destroying the database contents permanently. This distinction matters in production: `down` is a safe restart, while `down -v` is a full reset. In this assignment, `down -v` was demonstrated explicitly to show that the volume (and its Sakila data) was wiped, and re-running `up -d` started with a fresh database.

---

### 5. CI/CD Pipeline Design Decisions

The pipeline was ordered lint → test → build → security-scan to implement "fail fast" logic: linting is cheap (seconds) and catches trivial style errors before spending minutes running a full test suite or building a Docker image. If lint fails, no compute is wasted on downstream jobs. Tests run next, because there is no value in building an image for broken code. The build job comes only after tests pass, and the security scan is last because it has no effect on whether the code is deployable — it is informational. The security scan uses `exit-code: 0` intentionally: failing the entire pipeline on CVEs in the base Python image would block all deployments, since many CVEs in base images have no available fix. The correct response is to report them (uploaded as a workflow artifact) and track them separately. Concurrency grouping (`concurrency: group: ${{ github.ref }}`) prevents resource waste when developers push rapid successive commits to the same branch — a new push cancels the still-running pipeline from the previous commit, ensuring only the latest code is being validated at any time.

---

### 6. Production Readiness Assessment

If this application were deployed to real production, at least three additional practices would be essential. First, **secrets management**: passwords and API keys should never be in `.env` files on servers — instead, a dedicated secrets manager (AWS Secrets Manager, HashiCorp Vault, or GitHub Actions Secrets with OIDC) should inject credentials at runtime, with automatic rotation. Second, **monitoring and observability**: the application needs structured logging (e.g., JSON logs shipped to a log aggregator like Loki or CloudWatch), metrics exposure (Prometheus `/metrics` endpoint), and alerting rules so that errors or latency spikes trigger notifications before users report them. The `HEALTHCHECK` in the Dockerfile is a starting point, but it is not a substitute for application-level metrics. Third, **container orchestration with Kubernetes**: Docker Compose is suitable for a single machine, but production workloads require Kubernetes for self-healing (automatic pod restarts), horizontal scaling, rolling deployments with zero downtime, and resource scheduling across multiple nodes. The `depends_on` and restart policies in Compose would be replaced by Kubernetes `Deployments`, `Services`, `ConfigMaps`, and `Secrets`, providing far greater reliability and operational control.

---

*End of Part D Report — Abtaha | f2022-553 | Spring 2026*
