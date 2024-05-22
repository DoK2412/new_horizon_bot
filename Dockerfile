FROM python:3.11-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt --root-user-action=ignore

COPY ./ /code/

CMD ["python", "./app.py", "--host", "0.0.0.0", "--port", "8083"]