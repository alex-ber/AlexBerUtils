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


RUN set -ex && \
    #latest pip,setuptools,wheel
    pip install --upgrade pip==23.2.1 setuptools==68.0.0 wheel==0.36.1 && \
    #because of upgrade of PyYAML
    pip install -r etc/requirements.txt && \
    pip install -r etc/requirements-env.txt && \
    pip install -r etc/requirements-yml.txt && \
    pip install -r etc/requirements-fabric.txt && \
    pip install -r etc/requirements-md.txt && \
    pip install -r etc/requirements-tests.txt


#CMD ["/bin/sh"]
CMD tail -f /dev/null


#docker rmi -f utils-i
#docker rm -f utils
##docker build --no-cache --squash . -t utils-i
#docker build . -t utils-i
#docker exec -it $(docker ps -q -n=1) bash
#docker tag utils-i alexberkovich/alex_ber_utils:0.6.6
#docker push alexberkovich/alex_ber_utils:0.6.6
# EOF
