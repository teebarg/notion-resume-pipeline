FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

EXPOSE 3000

# Don't copy source — mount it as a volume instead
CMD ["npm", "run", "dev"]