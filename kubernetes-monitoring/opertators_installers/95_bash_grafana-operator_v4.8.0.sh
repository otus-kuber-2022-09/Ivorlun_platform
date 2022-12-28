#! /bin/bash

DIR="grafana_operator"
PRE_URL="https://raw.githubusercontent.com/grafana-operator/grafana-operator/v4.8.0/deploy/manifests/v4.8.0"

mkdir $DIR && cd $DIR
curl -sLO $PRE_URL/crds.yaml
curl -sLO $PRE_URL/deployment.yaml
curl -sLO $PRE_URL/kustomization.yaml
curl -sLO $PRE_URL/rbac.yaml
cd ..

kubectl delete -k $DIR || rm -rf $DIR
