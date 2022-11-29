# Ivorlun_platform
Ivorlun Platform repository


# Homework 2 (Intro)
### Задание. Разберитесь почему все pod в namespace kube-system восстановились после удаления.


Большая часть компонентов контроллируется с помощью самого minikube, имеет соответствующее описание при вызове `k -n kube-system describe po kube-apiserver-minikube` имеет вид `Controlled By:  Node/minikube` и суффикс `-minikube`:
```
etcd-minikube
kube-apiserver-minikube
kube-controller-manager-minikube
kube-scheduler-minikube
```
Насколько я понимаю, minikube start вызывает `kubeadm init`, который в свою очередь и запускает поочерёдно все компоненты control-plane.

Последовательность инициализации компонентов кластера:
```
The "init" command executes the following phases:

preflight                    Run pre-flight checks
certs                        Certificate generation
  /ca                          Generate the self-signed Kubernetes CA to provision identities for other Kubernetes components
  /apiserver                   Generate the certificate for serving the Kubernetes API
  /apiserver-kubelet-client    Generate the certificate for the API server to connect to kubelet
  /front-proxy-ca              Generate the self-signed CA to provision identities for front proxy
  /front-proxy-client          Generate the certificate for the front proxy client
  /etcd-ca                     Generate the self-signed CA to provision identities for etcd
  /etcd-server                 Generate the certificate for serving etcd
  /etcd-peer                   Generate the certificate for etcd nodes to communicate with each other
  /etcd-healthcheck-client     Generate the certificate for liveness probes to healthcheck etcd
  /apiserver-etcd-client       Generate the certificate the apiserver uses to access etcd
  /sa                          Generate a private key for signing service account tokens along with its public key
kubeconfig                   Generate all kubeconfig files necessary to establish the control plane and the admin kubeconfig file
  /admin                       Generate a kubeconfig file for the admin to use and for kubeadm itself
  /kubelet                     Generate a kubeconfig file for the kubelet to use *only* for cluster bootstrapping purposes
  /controller-manager          Generate a kubeconfig file for the controller manager to use
  /scheduler                   Generate a kubeconfig file for the scheduler to use
kubelet-start                Write kubelet settings and (re)start the kubelet
control-plane                Generate all static Pod manifest files necessary to establish the control plane
  /apiserver                   Generates the kube-apiserver static Pod manifest
  /controller-manager          Generates the kube-controller-manager static Pod manifest
  /scheduler                   Generates the kube-scheduler static Pod manifest
etcd                         Generate static Pod manifest file for local etcd
  /local                       Generate the static Pod manifest file for a local, single-node local etcd instance
upload-config                Upload the kubeadm and kubelet configuration to a ConfigMap
  /kubeadm                     Upload the kubeadm ClusterConfiguration to a ConfigMap
  /kubelet                     Upload the kubelet component config to a ConfigMap
upload-certs                 Upload certificates to kubeadm-certs
mark-control-plane           Mark a node as a control-plane
bootstrap-token              Generates bootstrap tokens used to join a node to a cluster
kubelet-finalize             Updates settings relevant to the kubelet after TLS bootstrap
  /experimental-cert-rotation  Enable kubelet client certificate rotation
addon                        Install required addons for passing conformance tests
  /coredns                     Install the CoreDNS addon to a Kubernetes cluster
  /kube-proxy                  Install the kube-proxy addon to a Kubernetes cluster

```

А kube-proxy и coredns не входят в control plane, а относятся к worker-ноде, в связи с чем контроллируются уже стандартными контроллерами типа daemonset-а и replicaset-а.
```
Controlled By:  DaemonSet/kube-proxy
Controlled By:  ReplicaSet/coredns-64897985d
```

### Задание. Dockerfile и Pod с reverse-proxy

Использую образ bitnami nginx, который уже использует 1001 пользователя и /app as root https://github.com/bitnami/containers/blob/b8ecc1fc8ebd38d60bb09c348814c16811c58d69/bitnami/nginx/1.23/debian-11/Dockerfile#L55.

1. scheduler определил, на какой ноде запускать pod
2. kubelet скачал необходимый образ и запустил контейнер
docker pull ivorlun/bitnami-nginx-8000:1.0

### Hipster Shop | Задание со * (Frontend pod unhealthy)

При вызове `k logs pods/frontend` обнаруживается ошибка `panic: environment variable "PRODUCT_CATALOG_SERVICE_ADDR" not set`. После её устранения, последовательно можно выяснить, что приложению не хватает для запуска переменных, указанных в данном манифесте: https://github.com/GoogleCloudPlatform/microservices-demo/blob/712da1fe6be18de9630e2473e0d70d6654412811/kubernetes-manifests/frontend.yaml#L80.
После их включения в свой манифест, ошибки запуска пропадают.

