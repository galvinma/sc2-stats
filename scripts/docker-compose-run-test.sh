if [ -z "${SC2_STATS_APP_ROOT}" ]; then
    echo "Required variable SC2_STATS_APP_ROOT is unset."
    exit 1
fi

cd $SC2_STATS_APP_ROOT && \
$SC2_STATS_APP_ROOT/scripts/docker-build.sh && \
COMPOSE_ENV_FILES=$SC2_STATS_APP_ROOT/test/.env docker compose run \
    sc2-stats-api alembic -c /app/backend/alembic.ini upgrade head && \
COMPOSE_ENV_FILES=$SC2_STATS_APP_ROOT/test/.env docker compose run \
    --rm \
    -it \
    --remove-orphans \
    --entrypoint=python \
    sc2-stats-test \
    -m pytest \
    -vvvs
