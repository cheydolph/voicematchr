# voicematchr

An application to help your voice get closer to voice of your choice!

## Docker Commands

# 1. Stop and remove all containers, networks defined in docker-compose.yml

sudo docker compose down

# 2. Remove dangling images, stopped containers, unused networks, and build cache

sudo docker system prune -f

# 3. Rebuild all images from scratch (no cached layers)

sudo docker compose build --no-cache

# 4. Start all services in detached mode

sudo docker compose up -d

# 5. Confirm container status

sudo docker compose ps

# 6. Tail logs for the VoiceMatchr service specifically

sudo docker compose logs -f voicematchr-service
