FROM alexberkovich/alpine-anaconda3:0.1.1-slim

COPY requirements.txt etc/requirements.txt
COPY requirements-env.txt etc/requirements-env.txt
COPY requirements-yml.txt etc/requirements-yml.txt
COPY requirements-fabric.txt etc/requirements-fabric.txt
COPY requirements-md.txt etc/requirements-md.txt
COPY requirements-tests.txt etc/requirements-tests.txt


RUN set -ex && \
    #latest pip,setuptools,wheel
    pip install --upgrade pip==20.3.1 setuptools==51.0.0 wheel==0.36.1 && \
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
##docker build --squash . -t utils-i
#docker build . -t utils-i
#docker exec -it $(docker ps -q -n=1) bash
#docker tag utils-i alexberkovich/alex_ber_utils:0.6.3
#docker push alexberkovich/alex_ber_utils:0.6.3
# EOF
