FROM alexberkovich/ubuntu2404-snapshot:2026-08-06

#[HARDWARE_CONFIG]: Deterministic execution and compilation flags
# Consolidated environment variables to reduce layer allocation overhead.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/.uv-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/opt/python
    #PATH="/app/.venv/bin:$PATH"
    #Add virtual environment to PATH so standard "python" works everywhere


WORKDIR /app


#[HARDWARE_BRIDGE]: Injecting UV Compiler (AOT Dependency Graph Resolver)
#https://github.com/astral-sh/uv/pkgs/container/uv/1073952945?tag=0.11.33-python3.12-trixie
COPY --from=ghcr.io/astral-sh/uv:0.11.33@sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7 /uv /uvx /bin/

#[RUNTIME_ENVIRONMENT]: Deterministic APT Projection & Root Python Allocation
RUN set -ex && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        nano && \
    rm -rf /var/lib/apt/lists/* && \
    echo 'set syntax "none"' >> /nanorc && \
    # Have uv fetch Python 3.10.20 and create a blank virtual environment \
    uv venv --python 3.10.20 /app/.venv

COPY . .


RUN set -ex && \
     # latest pip,setuptools,wheel
     # reason for setuptools==65.6.3
     # https://stackoverflow.com/questions/76043689/pkg-resources-is-deprecated-as-an-api#comment136784284_76044568 \
     # #uv run python -m piptools compile --no-strip-extras requirements.in \
     uv pip install --no-cache-dir pip==23.1.2 setuptools==65.6.3 pip-tools==7.3.0 && \
     uv pip install --no-cache-dir \
        -r requirements.txt \
        -r requirements-env.txt \
        -r requirements-yml.txt \
        -r requirements-fabric.txt \
        -r requirements-np.txt \
        -r requirements-tests.txt \
        -r requirements-piptools.txt \
        -r requirements-structlog.txt


RUN set -ex && \
    uv pip install --no-cache-dir twine==6.2.0


#[PROJECT_INJECTION]: Finalize Symbol Table Linkage
RUN set -ex && \
    chmod -R 777 /app/.venv && \
    chmod -R 755 /opt/python && \
    chmod -R 777 /tmp/.uv-cache && \
    mkdir -p /app/logs && \
    chmod -R 777 /app/logs


#CMD ["/bin/sh"]
#https://docs.docker.com/reference/build-checks/json-args-recommended/
#CMD tail -f /dev/null
CMD ["sleep", "infinity"]
#SHELL tail -f /dev/null





#docker system prune --all
#
#docker rmi -f utils-i
#docker rm -f utils
##docker build --no-cache --squash . -t utils-i
#docker build --no-cache --progress=plain . -t utils-i

#docker run -it utils-i
# The --entrypoint /bin/bash flag overrides the default script execution.
# You get a Linux command line INSIDE the container.
#docker run --rm -it --entrypoint /bin/bash utils-i

# ---[PyPI PUBLISHING PIPELINE] ---
# uv build
# Allocate token in RAM (Replace YOUR_TOKEN):
# export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN"
# Transmit artifacts to WAN (PyPI):
# uv publish 


#docker exec -it $(docker ps -q -n=1) bash
#docker tag utils-i alexberkovich/alex_ber_utils:0.14.0a
#docker tag utils-i alexberkovich/alex_ber_utils:latest
#docker push alexberkovich/alex_ber_utils:0.14.0a
#docker push alexberkovich/alex_ber_utils:latest
# EOF
