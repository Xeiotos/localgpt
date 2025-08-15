# Build stage
FROM node:22-alpine AS builder
WORKDIR /app

COPY frontend/package*.json ./
# include devDependencies for the build; cache npm for speed
RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend/ ./
RUN npm run build

# Production stage
FROM nginx:1.27-alpine

# Serve the SPA
COPY --from=builder /app/build /usr/share/nginx/html

# Minimal SPA + API proxy (with proper WS handling)
RUN printf '%s\n' \
  'map $http_upgrade $connection_upgrade { default upgrade; "" close; }' \
  'server {' \
  '  listen 80;' \
  '  root /usr/share/nginx/html;' \
  '  index index.html;' \
  '  location / { try_files $uri $uri/ /index.html; }' \
  '  location /api/ {' \
  '    proxy_pass http://orchestrator:8000;' \
  '    proxy_http_version 1.1;' \
  '    proxy_set_header Upgrade $http_upgrade;' \
  '    proxy_set_header Connection $connection_upgrade;' \
  '    proxy_set_header Host $host;' \
  '    proxy_read_timeout 300s;' \
  '  }' \
  '}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
