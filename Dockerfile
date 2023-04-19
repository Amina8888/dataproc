FROM python:3.8-slim-buster

#WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Define environment variable
ENV GOOGLE_PROJECT_ID="artful-fragment-380106"

COPY main.py .

CMD [ "python3", "main.py"]