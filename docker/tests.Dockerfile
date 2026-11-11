# syntax=docker/dockerfile:1.7
# Контейнер запуска тестов: выкачивает репозиторий, ставит зависимости, запускает этап.
#   docker build -f docker/tests.Dockerfile \
#     --build-arg REPO_URL=https://github.com/<owner>/<repo>.git --build-arg GIT_REF=<sha|branch> \
#     -t wildlife-tests .
#   docker run --rm -v "$PWD/results:/results" wildlife-tests unit|integration|e2e
# Без REPO_URL берётся локальный контекст сборки (удобно до первого push).
FROM python:3.12-slim

ARG REPO_URL=""
ARG GIT_REF=""

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Зависимости ставятся до клонирования: слой кэшируется между коммитами.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /workspace
COPY . /tmp/local-src
# Токен (для приватного репозитория) передаётся BuildKit-секретом и не попадает в слои образа.
RUN --mount=type=secret,id=git_token,required=false \
    set -eu; \
    if [ -n "$REPO_URL" ]; then \
        echo "[tests-image] git: $REPO_URL @ ${GIT_REF:-HEAD}"; \
        git init -q .; \
        git remote add origin "$REPO_URL"; \
        if [ -s /run/secrets/git_token ]; then \
            export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.extraHeader \
                GIT_CONFIG_VALUE_0="Authorization: Basic $(printf 'x-access-token:%s' "$(cat /run/secrets/git_token)" | base64 -w0)"; \
        fi; \
        git fetch -q --depth 1 origin "${GIT_REF:-HEAD}"; \
        git -c advice.detachedHead=false checkout -q FETCH_HEAD; \
        git log -1 --format='[tests-image] commit %H %s'; \
    else \
        echo "[tests-image] REPO_URL не задан — используется локальный контекст сборки"; \
        cp -a /tmp/local-src/. .; \
    fi; \
    rm -rf /tmp/local-src

RUN pip install -r requirements.txt

ENV RESULTS_ROOT=/results
VOLUME ["/results"]
ENTRYPOINT ["bash", "ci/run-tests.sh"]
CMD ["unit"]
