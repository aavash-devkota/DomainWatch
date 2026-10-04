FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY domainwatch ./domainwatch
RUN pip install --no-cache-dir .
VOLUME /root/.domainwatch
EXPOSE 8080
ENTRYPOINT ["domain-monitor"]
CMD ["run", "-c", "/root/.domainwatch/config.yaml"]
