#FROM alexberkovich/alpine-anaconda3:0.3.2-slim

#ARG ARCH=
ARG ARCH=amd64
FROM --platform=linux/${ARCH} alexberkovich/alpine-python3:0.3.5
ARG ARCH
ENV ARCH=${ARCH}

RUN set -ex && \
   echo $ARCH > /etc/ARCH


COPY requirements.txt etc/requirements.txt
COPY requirements-env.txt etc/requirements-env.txt
COPY requirements-yml.txt etc/requirements-yml.txt
COPY requirements-fabric.txt etc/requirements-fabric.txt
COPY requirements-md.txt etc/requirements-md.txt
COPY requirements-tests.txt etc/requirements-tests.txt
COPY requirements-piptools.txt etc/requirements-piptools.txt



RUN set -ex && \
     #latest pip,setuptools,wheel
     python -m pip install --no-cache-dir --upgrade pip==23.1.2 setuptools==67.8.0  \
         #python -Wignore::DeprecationWarning -m piptools compile --no-strip-extras requirements.in \
         wheel==0.36.1 pip-tools==7.3.0 && \
     python -Wignore::DeprecationWarning -m pip install --no-cache-dir -r /etc/requirements.txt \
        -r etc/requirements-env.txt -r etc/requirements-yml.txt -r etc/requirements-fabric.txt \
        -r etc/requirements-md.txt -r etc/requirements-tests.txt -r etc/requirements-piptools.txt


#CMD ["/bin/sh"]
CMD tail -f /dev/null

#docker system prune --all
#
#docker rmi -f utils-i
#docker rm -f utils
##docker build --no-cache --squash . -t utils-i
#docker build --no-cache . -t utils-i
#docker exec -it $(docker ps -q -n=1) bash
#docker tag utils-i alexberkovich/alex_ber_utils:0.8.0
#docker push alexberkovich/alex_ber_utils:0.8.0
# EOF
