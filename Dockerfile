#FROM alexberkovich/alpine-anaconda3:0.3.2-slim

#ARG ARCH=
ARG ARCH=amd64
FROM --platform=linux/${ARCH} alexberkovich/alpine-python39:0.4.0
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
     #latest pip,setuptools,wheel \
     #reason for setuptools==65.6.3 \
     #https://stackoverflow.com/questions/76043689/pkg-resources-is-deprecated-as-an-api#comment136784284_76044568 \
     python -m pip install --no-cache-dir --upgrade pip==23.1.2 setuptools==65.6.3  \
             #python -m piptools compile --no-strip-extras requirements.in \
         pip-tools==7.3.0 && \
     python -m pip install --no-cache-dir -r /etc/requirements.txt \
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
