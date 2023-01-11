#! /bin/bash
kubectl create -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.61.1/bundle.yaml || \
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.61.1/bundle.yaml
