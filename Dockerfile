FROM alexberkovich/alpine-anaconda3:0.3.2-slim



COPY requirements.txt etc/requirements.txt
COPY requirements-env.txt etc/requirements-env.txt
COPY requirements-yml.txt etc/requirements-yml.txt
COPY requirements-fabric.txt etc/requirements-fabric.txt
COPY requirements-np.txt etc/requirements-np.txt
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
        -r etc/requirements-np.txt \
        -r etc/requirements-tests.txt -r etc/requirements-piptools.txt



#CMD ["/bin/sh"]
#https://docs.docker.com/reference/build-checks/json-args-recommended/
#CMD tail -f /dev/null
CMD ["tail", "-f", "/dev/null"]
#SHELL tail -f /dev/null


#docker system prune --all
#
#docker rmi -f utils-i
#docker rm -f utils
##docker build --no-cache --squash . -t utils-i
#docker build --progress=plain . -t utils-i
#docker exec -it $(docker ps -q -n=1) bash
#docker tag utils-i alexberkovich/alex_ber_utils:0.12.2
#docker tag utils-i alexberkovich/alex_ber_utils:latest
#docker push alexberkovich/alex_ber_utils:0.12.2
#docker push alexberkovich/alex_ber_utils:latest
# EOF
