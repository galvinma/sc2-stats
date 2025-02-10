if [ -z "${SC2_STATS_APP_ROOT}" ]; then
    echo "Required variable SC2_STATS_APP_ROOT is unset."
    exit 1
fi

cd $SC2_STATS_APP_ROOT && \
    $SC2_STATS_APP_ROOT/scripts/docker-build.sh && \
    docker compose up
