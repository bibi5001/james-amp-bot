FROM python:3.9-slim
RUN pip install matrix-nio requests flask
WORKDIR /app
COPY amp-bot.py .
CMD ["python", "amp-bot.py"]
