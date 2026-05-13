# CloudBase Container Deployment

## Applicable directory

This guide applies to the backend project under this directory:

- `backend/`

The container entry file is:

- `Dockerfile`

The actual FastAPI app entry is:

- `functions/user-story-api/main.py`

## Current startup behavior

The container starts the service with the following command:

```sh
uvicorn main:app --host 0.0.0.0 --port ${PORT:-80}
```

This means:

- CloudBase must expose or inject the `PORT` environment variable
- The service listens on `0.0.0.0`
- The default internal port is `80`

## Files already prepared

You already have:

- `Dockerfile`
- `.dockerignore`

The `.dockerignore` file prevents `.env`, caches, logs, and Git metadata from entering the image.

## Recommended deployment method

Use **CloudBase container deployment**, not the original cloud function handler configuration.

Reason:

- Your container uses `uvicorn main:app`
- The file `cloudbaserc.json` is for the older cloud function style
- Container deployment does not need `main.handler` as the startup entry

## What to configure in CloudBase

When creating a container service in CloudBase, use these values.

### 1. Build context

Set the build context to the backend root directory:

```text
backend
```

### 2. Dockerfile path

Use:

```text
Dockerfile
```

### 3. Container port

Set the service port to:

```text
80
```

If CloudBase automatically injects `PORT`, the current Dockerfile can use it directly.

### 4. Environment variables

Do not upload the local `.env` file.

Add the following environment variable in CloudBase manually:

```text
DEEPSEEK_API_KEY=your_real_key
```

Optional variables if you want to keep them:

```text
DEBUG=true
API_PORT=80
API_HOST=0.0.0.0
```

In practice, the key variable is `DEEPSEEK_API_KEY`.

## Suggested routing

Your FastAPI app exposes the same endpoints both at the root path and under `/api`.

That means you can either call the service directly at the root path, or keep using an `/api` prefix from the frontend:

```text
/api
```

The internal health check path should use the real route path:

```text
/health
```

The external access path can still be:

```text
/api/health
```

## Local validation before upload

From the backend directory, you can validate with Docker:

### Build image

```sh
docker build -t user-story-api .
```

### Run container

```sh
docker run --rm -p 8000:80 -e DEEPSEEK_API_KEY=your_real_key user-story-api
```

### Test health endpoint

Open:

```text
http://localhost:8000/health
```

If you are simulating the `/api` prefix through a gateway, the external path may become:

```text
http://your-domain/api/health
```

## Important notes

### 1. Do not rely on the local `.env` file in production

Use CloudBase environment variables instead.

### 2. `cloudbaserc.json` is not the main config for this container deployment

You may keep it in the repository, but it is not the runtime entry for the container.

### 3. The folder name `user-story-api` is acceptable for now

Because the Dockerfile copies that directory into `/app` and then runs `main.py` from there, it works.

If you later want a cleaner Python package structure, rename it to something like:

```text
user_story_api
```

## Deployment checklist

- Docker build context is `backend`
- Dockerfile path is `backend/Dockerfile`
- Service port is `80`
- CloudBase environment variable `DEEPSEEK_API_KEY` is set
- `.env` is not uploaded into the image
- Frontend can use either root routes or `/api` routes

## Troubleshooting

### Container starts but endpoints return 404

Possible cause:

- Frontend or gateway is calling a different path variant than the backend exposes

Check whether you are visiting `/health` or `/api/health`. Both are supported now.

### Container starts but model calls fail

Possible cause:

- `DEEPSEEK_API_KEY` is missing in CloudBase environment variables

### Build succeeds but startup fails

Possible cause:

- The platform is not using the backend directory as the Docker build context
- The Dockerfile path is incorrect
- The service port is not mapped to `80`
