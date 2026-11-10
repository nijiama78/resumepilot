# ---------- 构建阶段：Vite 打包 ----------
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# VITE_API_BASE 在构建期注入（默认相对路径，走 nginx 反代）
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# ---------- 运行阶段：nginx 托管静态文件 + 反代 /api ----------
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
