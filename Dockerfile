FROM python:3.6

EXPOSE 5001

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD ./requirements.txt /usr/src/app/requirements.txt
COPY . /usr/src/app

RUN pip install -r requirements.txt


