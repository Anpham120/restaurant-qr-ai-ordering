FROM node:24-alpine AS build
WORKDIR /app

ARG VITE_API_BASE_URL=https://api.cmcrestaurant.app/api
ARG VITE_ORDER_HUB_URL=https://api.cmcrestaurant.app/hubs/orders
ARG VITE_USE_MOCK_CHAT=false
ARG VITE_USE_MOCK_ORDER=false
ARG VITE_USE_MOCK_MENU=false

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ORDER_HUB_URL=$VITE_ORDER_HUB_URL
ENV VITE_USE_MOCK_CHAT=$VITE_USE_MOCK_CHAT
ENV VITE_USE_MOCK_ORDER=$VITE_USE_MOCK_ORDER
ENV VITE_USE_MOCK_MENU=$VITE_USE_MOCK_MENU

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build:all

FROM nginx:1.27-alpine AS runtime
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/customer-web/dist /usr/share/nginx/html/customer
COPY --from=build /app/apps/admin-web/dist /usr/share/nginx/html/admin
COPY --from=build /app/apps/kitchen-web/dist /usr/share/nginx/html/kitchen
COPY --from=build /app/apps/staff-web/dist /usr/share/nginx/html/staff

EXPOSE 80
