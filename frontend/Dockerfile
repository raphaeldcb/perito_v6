# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

COPY --from=builder /app/dist ./dist
COPY package.json ./

EXPOSE 3000

# Run the frontend
CMD ["serve", "-s", "dist", "-l", "3000"]
