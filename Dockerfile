# Frontend production Dockerfile — multi-stage build for the Next.js app.
# Used by docker-compose.prod.yml (build context: repo root).
FROM node:22-alpine AS deps

WORKDIR /app/aara-frontend

COPY aara-frontend/package.json aara-frontend/package-lock.json ./
RUN npm ci

# Build the frontend
FROM node:22-alpine AS builder

WORKDIR /app/aara-frontend

COPY --from=deps /app/aara-frontend/node_modules ./node_modules
COPY aara-frontend ./
RUN npm run build

# Production image
FROM node:22-alpine AS production

WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy the standalone Next.js server output (server.js lands at the app root
# since Next traces file dependencies relative to aara-frontend/package.json).
COPY --from=builder /app/aara-frontend/.next/standalone/ ./
COPY --from=builder /app/aara-frontend/.next/static ./.next/static
COPY --from=builder /app/aara-frontend/public ./public

RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000 || exit 1

CMD ["node", "server.js"]
