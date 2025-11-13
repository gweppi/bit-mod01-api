FROM python:3.13.5-alpine3.22

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p static

COPY . .

EXPOSE 8080
CMD [ "python", "app.py" ]