# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config if needed (default works for SPA with API proxy handled separately)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
