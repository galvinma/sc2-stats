cd backend && \
docker build . -t sc2-stats-backend:latest && \
cd .. && \
cd db && \
docker build . -t sc2-stats-db:latest 