#! /bin/bash
kubectl delete -n prometheus -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.61.1/bundle.yaml
