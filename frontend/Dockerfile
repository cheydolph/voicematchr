# Stage 1: produce the Nitro server bundle.
FROM node:22-bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy the manifests alone first so the dependency layer is cached across source edits.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: run the bundle. Nothing from the build toolchain follows it here.
FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production
ENV PORT=3000
ENV HOST=0.0.0.0

WORKDIR /app

# The Nitro node-server preset emits a self-contained bundle: .output/server holds the server entrypoint with its dependencies inlined, .output/public holds the client assets. No node_modules install is needed at runtime.
COPY --from=build --chown=node:node /build/.output ./.output

# node:* images ship a non-root `node` user (uid 1000). Running as it keeps the
# container off root, matching the appuser convention in voicematchr-service.
USER node

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
