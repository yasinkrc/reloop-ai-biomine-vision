# BioMine Vision frontend — Next.js standalone üretim imajı
FROM node:20-alpine AS bagimliliklar
WORKDIR /uygulama
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

FROM node:20-alpine AS insaat
WORKDIR /uygulama
COPY --from=bagimliliklar /uygulama/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS calisma
WORKDIR /uygulama
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=insaat /uygulama/public ./public
COPY --from=insaat /uygulama/.next/standalone ./
COPY --from=insaat /uygulama/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
