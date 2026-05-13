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
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

This means:

- CloudBase must expose or inject the `PORT` environment variable
- The service listens on `0.0.0.0`
- The default internal port is `8000`

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
8000
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
API_PORT=8000
API_HOST=0.0.0.0
```

In practice, the key variable is `DEEPSEEK_API_KEY`.

## Suggested routing

Your FastAPI app currently defines `root_path="/api"` in `functions/user-story-api/main.py`.

That means the cleanest deployment approach is to configure CloudBase routing so that the service is mounted under:

```text
/api
```

Then your health check path will usually be:

```text
/api/health
```

If you want to deploy directly at the domain root instead of `/api`, you may need to remove or adjust `root_path` later.

## Local validation before upload

From the backend directory, you can validate with Docker:

### Build image

```sh
docker build -t user-story-api .
```

### Run container

```sh
docker run --rm -p 8000:8000 -e DEEPSEEK_API_KEY=your_real_key user-story-api
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
- Service port is `8000`
- CloudBase environment variable `DEEPSEEK_API_KEY` is set
- `.env` is not uploaded into the image
- Routing is configured consistently with `/api` if you keep `root_path="/api"`

## Troubleshooting

### Container starts but endpoints return 404

Possible cause:

- CloudBase route prefix does not match the app `root_path`

Check whether you are visiting `/health` or `/api/health`.

### Container starts but model calls fail

Possible cause:

- `DEEPSEEK_API_KEY` is missing in CloudBase environment variables

### Build succeeds but startup fails

Possible cause:

- The platform is not using the backend directory as the Docker build context
- The Dockerfile path is incorrect
- The service port is not mapped to `8000`
