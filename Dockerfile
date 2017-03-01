FROM python:3.5-slim
RUN apt-get update
RUN apt-get install -y git

ADD requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt

ADD . ./genotype-to-model
WORKDIR genotype-to-model
ENV PYTHONPATH $PYTHONPATH:/genotype-to-model/genotype_to_model/comms

EXPOSE 50053

ENTRYPOINT ["python"]
CMD ["manage.py"]
