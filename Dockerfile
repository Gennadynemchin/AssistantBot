FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . /app
RUN chmod a+x tg_bot.py
ENTRYPOINT [ "python" ]
CMD ["./tg_bot.py"]