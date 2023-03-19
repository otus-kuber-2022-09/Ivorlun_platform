FROM python:3.11-alpine
ENV NAMESPACE=default
COPY templates templates
COPY mysql-operator.py mysql-operator.py
RUN pip install kopf jinja2 kubernetes pyyaml
CMD kopf run --namespace ${NAMESPACE} mysql-operator.py
