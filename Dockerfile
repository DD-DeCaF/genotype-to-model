FROM biosustain/cameo:cc6a5dbc388f
RUN apt-get -y update && apt-get install -y git  # TODO: remove after model-modification functionality goes to driven

ADD requirements.txt requirements.txt
RUN /bin/bash -c "pip install --upgrade -r requirements.txt"

ADD . ./genotype-to-model
WORKDIR genotype-to-model
ENV PYTHONPATH $PYTHONPATH:/genotype-to-model/genotype_to_model/comms

ENTRYPOINT ["python"]
CMD ["manage.py"]
