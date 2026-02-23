FROM node:22-alpine

WORKDIR /app

# Copy package files and install
COPY package.json package-lock.json* ./
RUN npm ci --omit=dev

# Copy source
COPY tsconfig.json .
COPY src/ src/

# Create data directory
RUN mkdir -p data

EXPOSE 3000

# Use tsx for direct TypeScript execution
CMD ["npx", "tsx", "src/index.ts"]
