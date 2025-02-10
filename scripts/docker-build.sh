if [ -z "${SC2_STATS_APP_ROOT}" ]; then
    echo "Required variable SC2_STATS_APP_ROOT is unset."
    exit 1
fi

cd $SC2_STATS_APP_ROOT && \
cd backend && \
    docker build . --target base -t sc2-stats-backend:latest && \
    docker build . --target test -t sc2-stats-test:latest && \
cd .. && \
cd db && \
    docker build . -t sc2-stats-db:latest --no-cache
