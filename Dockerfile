FROM python:arm

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY ["bot.py", "secret.py", "/usr/src/app/"]

CMD ["python", "./bot.py"]
