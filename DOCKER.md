# Running Claude Code in a Docker sandbox (YOLO mode)

This guide runs Claude Code with `--dangerously-skip-permissions` ("YOLO mode")
safely. Normally that flag is risky because Claude can edit files and run
commands without asking. Inside a container it is safe: the container is an
isolation boundary, so Claude can only touch this project folder (which we mount
in) and the network ports we explicitly expose. Nothing else on your Windows
machine is reachable.

## Two places commands run (read this first)

Throughout this guide, commands run in one of two places. Do not mix them up.

- **PowerShell (Windows):** you only ever type `docker ...` commands here. This
  is how you build the image and start/stop the container.
- **Inside the container:** a Debian Linux bash shell that exists only while the
  container is running. You do not open it yourself. When the launch command
  starts `claude`, Claude Code is running inside the container, and any shell
  command it runs for you (uvicorn, npm, uv, git) runs there automatically. You
  just talk to Claude.

---

## Step 1 - Create the Dockerfile

Create a file named `Dockerfile.claude` in the project root
(`c:\ClaudeProjects\pm`) with this content:

```dockerfile
FROM node:22-bookworm

# Base tools your project needs: git, plus build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ca-certificates \
        curl \
        ripgrep \
        less \
    && rm -rf /var/lib/apt/lists/*

# uv (your Python package manager) - installed to /usr/local/bin so it's on PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | \
    env UV_INSTALL_DIR=/usr/local/bin sh

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Playwright: Chromium + its system libraries, baked in while we are still root
# (the dev user has no sudo). Browsers go to a shared path both users can read,
# so e2e tests run without a per-launch download. Keep the version in sync with
# frontend/package.json (@playwright/test).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx -y playwright@1.58.0 install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

# Non-root user matching a typical uid so mounted files stay writable
RUN userdel -r node 2>/dev/null || true
RUN useradd -m -s /bin/bash -u 1000 dev
USER dev
WORKDIR /work

# Pre-create the dependency mount points as dev. The shadow volumes
# (claude-pm-node, claude-pm-venv) mount here; a fresh named volume inherits the
# ownership of this image path, so creating them as dev makes npm ci / uv sync
# writable. Without this they would be root-owned and the install would fail.
RUN mkdir -p /work/frontend/node_modules /work/backend/.venv

# Treat CRLF working-tree files as LF when diffing, so a Windows-authored tree
# (CRLF) does not show every file as modified against LF commits. Sandbox-local;
# does not rewrite any files.
RUN git config --global core.autocrlf input

# Claude config/credentials live here; we mount a volume over it to persist
# login. Create it as dev FIRST so the named volume inherits dev ownership and
# the credentials file is writable (otherwise the mount point is root-owned).
RUN mkdir -p /home/dev/.claude
ENV CLAUDE_CONFIG_DIR=/home/dev/.claude

CMD ["bash"]
```

What each part does:

- `FROM node:22-bookworm` - start from the official Node 22 (current LTS) image
  on Debian "bookworm". Node gives you `npm` for Claude Code and your frontend;
  Debian gives you `apt` to add the other tools.
- The `apt-get` block installs `git` (version control), `curl` and
  `ca-certificates` (for downloading over HTTPS), `ripgrep` (fast search that
  Claude Code relies on), and `less` (paging). `--no-install-recommends` and the
  `rm -rf /var/lib/apt/lists/*` keep the image small.
- The `uv` block installs your Python package manager into `/usr/local/bin` so
  it is on the system `PATH` for every user.
- `npm install -g @anthropic-ai/claude-code` installs the Claude Code CLI
  globally so the `claude` command is available.
- The Playwright block installs Chromium **and** its Linux system libraries
  (`--with-deps`) at build time, while we still have root. Without this,
  `npm run test:e2e` fails in the container because headless Chromium cannot
  find shared libraries (`libnss3.so`, etc.) and the `dev` user has no `sudo` to
  add them. `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` and the `chmod` put the
  browser in a shared path the `dev` user can read, so e2e runs with no
  per-launch download. Pin the version to match `@playwright/test` in
  `frontend/package.json`.
- `mkdir -p /work/frontend/node_modules /work/backend/.venv` (as `dev`)
  pre-creates the shadow-volume mount points. A fresh named volume inherits the
  ownership of the image directory it mounts over, so making these `dev`-owned
  lets `npm ci`/`uv sync` write into them. Without it the mount points are
  root-owned and the installs fail with permission denied - the same bug the
  `.claude` directory line prevents.
- `git config --global core.autocrlf input` (run as `dev`) stops Linux git from
  reporting every file as modified. Your tree is CRLF (authored on Windows) but
  commits are LF; this tells git to normalize CRLF to LF when comparing, so the
  working tree matches the commits. It is sandbox-local and never rewrites files.
- `userdel ... node` and `useradd ... dev` replace the image's default user with
  a `dev` user whose uid is `1000`. Matching a normal uid means files Claude
  writes into your mounted project come out with sensible ownership rather than
  as root.
- `USER dev` switches to that user for everything after it.
- `WORKDIR /work` sets the working directory to `/work`; this is where your
  project folder gets mounted.
- `RUN mkdir -p /home/dev/.claude` creates the Claude config directory **as the
  `dev` user**. This line matters: when a fresh named volume is mounted over a
  directory, Docker copies that directory's ownership onto the volume. Creating
  it as `dev` first makes the volume writable; without it the mount point is
  root-owned and login cannot save credentials.
- `ENV CLAUDE_CONFIG_DIR=/home/dev/.claude` tells Claude Code to store its
  config and credentials there, so our volume captures them.
- `CMD ["bash"]` is the default command if you start the container without
  specifying one.

---

## Step 2 - Build the image

In PowerShell, from the project root:

```powershell
docker build -f Dockerfile.claude -t claude-sandbox .
```

- `docker build` turns the Dockerfile into a reusable image.
- `-f Dockerfile.claude` points at our Dockerfile (the default name is just
  `Dockerfile`; we use a custom name so it does not clash with anything).
- `-t claude-sandbox` tags (names) the image `claude-sandbox` so later commands
  can refer to it.
- `.` is the build context (the current folder). It tells Docker where to look
  for files the Dockerfile references.

Re-run this exact command whenever you change the Dockerfile or want a newer
Claude Code.

---

## Step 3 - One-time setup (create the login volume and sign in)

A container is thrown away when it exits, so your Claude login would be lost
each time. A **named volume** is persistent storage that survives across
containers. We create one and sign in once; every later launch reuses it.

```powershell
docker volume create claude-config
```

- Creates a persistent volume named `claude-config`. We will mount it at
  `/home/dev/.claude` so the login saved there outlives the container.

We also create two more volumes to hold the container's Linux-native
dependencies (explained in Step 4):

```powershell
docker volume create claude-pm-node
docker volume create claude-pm-venv
```

Now sign in once:

```powershell
docker run -it --rm `
  -v claude-config:/home/dev/.claude `
  claude-sandbox `
  claude
```

- `docker run` starts a new container from the image.
- `-it` gives it an interactive terminal so you can complete the login prompt.
- `--rm` deletes the container when it exits (your login is safe in the volume,
  not the container).
- `-v claude-config:/home/dev/.claude` mounts the volume at the config dir, so
  the saved credentials persist.
- `claude-sandbox` is the image to run.
- `claude` is the command to run inside it - here, just Claude Code so it walks
  you through sign-in.

Complete the browser sign-in, confirm you reach a Claude prompt, then exit
(`/exit` or Ctrl-C). The credentials now live in `claude-config` and are reused
automatically.

> If sign-in says it completed in the browser but credentials could not be
> saved, the volume is root-owned (an image built before the `mkdir` line).
> Fix: rebuild (Step 2), then `docker volume rm claude-config` and
> `docker volume create claude-config`, then run this sign-in step again.
>
> The same applies to the dependency volumes if they were created against an
> older image: a volume's ownership is fixed when it is first mounted, so
> rebuilding does not fix an existing one. Recreate them (they are empty until
> the Step 4a install anyway):
>
> ```powershell
> docker volume rm claude-pm-node claude-pm-venv
> docker volume create claude-pm-node
> docker volume create claude-pm-venv
> ```

---

## Step 4 - Launch Claude in YOLO mode (every time)

From the project root (`c:\ClaudeProjects\pm`):

```powershell
docker run -it --rm `
  -v "${PWD}:/work" `
  -v claude-config:/home/dev/.claude `
  -v claude-pm-node:/work/frontend/node_modules `
  -v claude-pm-venv:/work/backend/.venv `
  -p 8000:8000 `
  -p 3000:3000 `
  claude-sandbox `
  claude --dangerously-skip-permissions
```

- `-it` / `--rm` - interactive terminal; discard the container on exit.
- `-v "${PWD}:/work"` - **bind mount**: maps your current Windows folder into the
  container at `/work`. `${PWD}` is the folder you are in, so run this from the
  project root. This mount is the sandbox boundary - Claude can read and write
  only here.
- `-v claude-config:/home/dev/.claude` - reuses the login from Step 3.
- `-v claude-pm-node:/work/frontend/node_modules` and
  `-v claude-pm-venv:/work/backend/.venv` - **the cross-platform fix.** Your
  Windows `node_modules` and `.venv` hold binaries compiled for Windows; they
  cannot run on the container's Linux. These two volumes mount *over* those
  folders so the container uses its own Linux-native copies (kept in the
  volumes), while your Windows copies on disk stay untouched. A mount nested
  inside a bind mount simply shadows that subfolder. You install into them once
  (Step 4a).
- `-p 8000:8000` and `-p 3000:3000` - publish the container's ports 8000
  (backend) and 3000 (frontend dev) to the same ports on Windows, so you can
  open the app in your browser.
- `claude --dangerously-skip-permissions` - starts Claude Code in YOLO mode (no
  per-action approval prompts).

This drops you straight into Claude Code running inside the container.

### Step 4a - Install Linux dependencies (first launch only)

The first time you launch (and whenever `package-lock.json` or `uv.lock`
changes), the shadow volumes are empty, so ask Claude to install the Linux
builds. Claude runs these inside the container:

```bash
# frontend dependencies into claude-pm-node
cd /work/frontend && npm ci

# backend dependencies into claude-pm-venv
uv sync --project /work/backend
```

These write into the two volumes and persist, so later launches skip this step.
They do not touch your Windows `node_modules`/`.venv`.

---

## Step 5 - View the app in your Windows browser

Your `start.ps1` binds the server to `127.0.0.1`. Inside a container that means
the container's own loopback, which Docker's port forwarding cannot reach - so
the app would be invisible from Windows. Do not change the script. Instead, ask
Claude (in the running session) to start the app bound to `0.0.0.0`. Claude runs
these inside the container for you:

```bash
# backend
uv run --project backend --env-file .env uvicorn backend.main:app --host 0.0.0.0 --port 8000

# frontend dev (if needed)
npm run dev -- --hostname 0.0.0.0
```

`0.0.0.0` means "listen on all interfaces", which is what lets the `-p` port
mapping deliver traffic to it. This is safe because only the ports you mapped
are exposed. Then open `http://127.0.0.1:8000/` (and `:3000`) in Windows.

---

## Do the changes persist?

Yes. Because `-v "${PWD}:/work"` is a bind mount, `/work` in the container *is*
your Windows project folder. Every file Claude creates or edits in YOLO mode is
written straight to `c:\ClaudeProjects\pm` on disk. When you exit (and `--rm`
discards the container) the files remain. You can then use Claude normally on
Windows and continue exactly where the sandbox left off.

What lives inside Docker rather than your project folder, on purpose: your
Claude login (`claude-config`) and the container's Linux dependencies
(`claude-pm-node`, `claude-pm-venv`). These are separate from your Windows
`node_modules`/`.venv`, so neither side disturbs the other. Your code and config
changes always persist to the project folder.

---

## Tip: helper script

To avoid retyping the launch command, save this as `claude-yolo.ps1` somewhere
on your PATH, then `cd` to the project and run `claude-yolo`:

```powershell
docker run -it --rm `
  -v "${PWD}:/work" `
  -v claude-config:/home/dev/.claude `
  -v claude-pm-node:/work/frontend/node_modules `
  -v claude-pm-venv:/work/backend/.venv `
  -p 8000:8000 `
  -p 3000:3000 `
  claude-sandbox `
  claude --dangerously-skip-permissions
```
