FROM node:24-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=https://api.cmcrestaurant.app/api
ARG VITE_USE_MOCK_CHAT=false

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_USE_MOCK_CHAT=$VITE_USE_MOCK_CHAT

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
