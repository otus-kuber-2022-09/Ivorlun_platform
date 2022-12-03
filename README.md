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


# Homework 3 (Kubernetes-controllers)
## Init containers

A Pod can have multiple containers running apps within it, but it can also have one or more init containers, which are run before the app containers are started.

Init containers are exactly like regular containers, except:

    Init containers always run to completion.
    Each init container must complete successfully before the next one starts.

If a Pod's init container fails, the kubelet repeatedly restarts that init container until it succeeds. However, if the Pod has a restartPolicy of Never


Помимо init-контейнеров существуют poststart и prestop хуки
```
        lifecycle:
          preStop:
            exec:
              command: [ "/bin/bash", "-c", "sleep 5; kill -QUIT 1" ]
```

## Задание. Почему обновление ReplicaSet не повлекло обновление запущенных pod?

В нашем случае, replicaset controller следит за тем, чтобы pod-ов, которые попадают в область ответственности контроллера по label-ам, было указанное количество. При этом изменение информации в самих подах не входит в его зону ответственности. А так как подов уже было 3 и их количество не изменилось, то контроллер не предпринял никаких действий.
Для подобных случаев используют контроллер контроллеров - deployment.

ReplicaSet (так же как и устаревший replication controller) не заменяет поды при обновлении шаблона автоматически.

Официальная документация:
https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#deleting-just-a-replicaset
```
Once the original is deleted, you can create a new ReplicaSet to replace it. As long as the old and new .spec.selector are the same, then the new one will adopt the old Pods. However, it will not make any effort to make existing Pods match a new, different pod template. To update Pods to a new spec in a controlled way, use a Deployment, as ReplicaSets do not support a rolling update directly.
```

## ReplicaSet and Deployment

**ReplicaSet** - контроллер подов, следит за тем, чтобы количество подов, попадающих в выборку селектора, соответствовало желаемому количеству реплик. НЕ проверяет соответствие запущенных Podов шаблону.
**Deployment** - контроллер replicaSet-а, который имеет статусы развёртывания, команду rollout для управления ими и является де-факто предпочтительным деплоем pod-ов в кластер.
If a HorizontalPodAutoscaler (or any similar API for horizontal scaling) is managing scaling for a Deployment, don't set .spec.replicas.

### ReplicaSet and Deprecated Replication contorller
Убрали авто-генерацию селектора и добавили поддержку set-based селекторов:
было:
`selector: { app: nginx, tier: front, environment: stage }`
стало:
```
selector:
  matchLabels:
    app: nginx
  matchExpressions:
    - { key: tier, operator: In, values: [front] }
    - { key: environment, operator: NotIn, values: [prod] }
```

## Rollout strategies
https://fluxcd.io/flagger/usage/deployment-strategies/

The are two options "Recreate" or "RollingUpdate":
1. Rolling update strategy: Minimizes downtime at the cost of update speed. Pod-by-Pod.
1. Recreation Strategy: Causes downtime but updates quickly. Removing old RS with all pods than creating new one.


Also there are not in Kubernetes out of the box, but in general:
* Canary Strategy (Rolling update variation): Quickly updates for a select few users with a full rollout later. Updates part of application and routes part of traffic to new version with metrics scrapping.

* A/B Testing (dark testing) - only fo frontend. Canary for back and this one is for front. A/B Testing
For frontend applications that require session affinity you should use HTTP headers or cookies match conditions to ensure a set of users will stay on the same version for the whole duration of the canary analysis.

* Blue/Green with Traffic Mirroring
Traffic Mirroring is a pre-stage in a Canary (progressive traffic shifting) or Blue/Green deployment strategy. Traffic mirroring will copy each incoming request, sending one request to the primary and one to the canary service. The response from the primary is sent back to the user. The response from the canary is discarded. Metrics are collected on both requests so that the deployment will only proceed if the canary metrics are healthy.

### Recreate Deployment
All existing Pods are killed before new ones are created when .spec.strategy.type==Recreate.

### Rolling Update Deployment

Указывается либо в uint либо в процентах:
* **maxSurge** - максимальный оверхед подов (The absolute number is calculated from the percentage by rounding up. The default value is 25%.)
* **maxUnavailable** - максимальное количество недоступных (The absolute number is calculated from percentage by rounding down. The default value is 25%.)

* **.spec.progressDeadlineSeconds** is an optional field that specifies the number of seconds you want to wait for your Deployment to progress before the system reports back that the Deployment has failed progressing
* .**spec.minReadySeconds** is an optional field that specifies the minimum number of seconds for which a newly created Pod should be ready without any of its containers crashing, for it to be considered available.
* **.spec.revisionHistoryLimit** is an optional field that specifies the number of old ReplicaSets to retain to allow rollback.

## Deployment | Задание со *

#### Blue-green deployment:
1. Развертывание трех новых pod;
2. Удаление трех старых pod;
```
      strategy:
        type: RollingUpdate
        rollingUpdate:
          maxSurge: 100%
          maxUnavailable: 0
```
#### Reverse Rolling Update:
1. Удаление одного старого pod;
2. Создание одного нового pod;
3. …
```
      strategy:
        type: RollingUpdate
        rollingUpdate:
          maxSurge: 0
          maxUnavailable: 1
```

## Deployment | Rollback
`kubectl rollout undo deployment paymentservice --to-revision=1 | kubectl get rs -l app=paymentservice -w`

Можно смотреть историю и выбирать на какую ревизию откатиться
`kubectl rollout history deployment`

Пауза, если нужна
`kubectl rollout pause deployment/nginx-deployment`
## Kubectl WAIT
Есть возможность через kubectl ожидать выполнения определённых условий, например:
`k wait po -l app=paymentservice --for condition=Ready --timeout=90s`

## Job
```
apiVersion: batch/v1
kind: Job
metadata:
  name: very_good_job
spec:
  # Число попыток, перед Failed с нарастающим интервалом
  backoffLimit: 4
  # Максимальная продолжительность Job
  activeDeadlineSeconds: 60
  # Количество одновременно запущенных Podов
  parallelism: 3
  # Разрешить TTLController-у прибрать остатки, 0 - чистить сразу
  # На данный момент требует включить Feature Gate TTLAfterFinished
  ttlSecondsAfterFinished: 600
  # Суммарное число запусков Podов
  completions: 9
  template:
    spec:
      containers:
      ...
      restartPolicy: OnFailure # или Never
```
## CronJob
Генерация и запуск Job по расписанию:
1. Однократно в заданное время
1. Периодически
* Регулярные задачи останавливаются, если пропустили последние 100 запусков
* Также он отслеживает "наложение" задач по времени и может управлять такими ситуациями

```
spec:
  # Стандартный формат расписания для Cron
  schedule: "@hourly"
  # Сколько секунд есть для запуска задачи,
  # если пропустили запланированное время
  startingDeadlineSeconds: 200
  # Что делать с наложением задач во времени:
  #
  forbid - не запускать новую
  #
  allow - запускать параллельно
  #
  replace - удалять старые задачи
  concurrencyPolicy: replace
  # Притормозить планировщик
  suspend: false
  # Хранить ли историю запущенных задач
  successfulJobsHistoryLimit: 0
  failedJobsHistoryLimit: 0
  jobTemplate:
```

## Readiness and Liveness Probes

Liveness - когда контейнер вообще работает или его нужно запускать. Не обязательно при старте, а после длительного рантайма тоже.
Readiness - когда контейнер провёл бутстраппинг и готов принимать трафик.

The kubelet uses liveness probes to know when to restart a container. For example, liveness probes could catch a deadlock, where an application is running, but unable to make progress. Restarting a container in such a state can help to make the application more available despite bugs.

The kubelet uses readiness probes to know when a container is ready to start accepting traffic.

Пока readinessProbe для нового pod не станет успешной - Deployment не будет пытаться продолжить обновление.
Чтобы отследить успешность деплоя можно использовать `kubectl rollout status deployment/frontend`

описание pipeline, включающее в себя шаг развертывания и шаг отката, в самом простом случае может выглядеть так (синтаксис GitLab CI):
```
deploy_job:
  stage: deploy
  script:
    - kubectl apply -f frontend-deployment.yaml
    - kubectl rollout status deployment/frontend --timeout=60s

rollback_deploy_job:
  stage: rollback
  script:
    - kubectl rollout undo deployment/frontend
  when: on_failure
```

## DaemonSet

Типичные кейсы использования DaemonSet:
* Сетевые плагины;
* Утилиты для сбора и отправки логов (Fluent Bit, Fluentd, etc…);
* Различные утилиты для мониторинга (Node Exporter, etc…);
## nodeSelector

nodeSelector is the simplest recommended form of node selection constraint. You can add the nodeSelector field to your Pod specification and specify the node labels you want the target node to have. Kubernetes only schedules the Pod onto nodes that have each of the labels you specify.

## Affinity and anti-affinity

nodeSelector is the simplest way to constrain Pods to nodes with specific labels. Affinity and anti-affinity expands the types of constraints you can define. Some of the benefits of affinity and anti-affinity include:

    * The affinity/anti-affinity language is more expressive. nodeSelector only selects nodes with all the specified labels. Affinity/anti-affinity gives you more control over the selection logic.
    * You can indicate that a rule is soft or preferred, so that the scheduler still schedules the Pod even if it can't find a matching node.
    * You can constrain a Pod using labels on other Pods running on the node (or other topological domain), instead of just node labels, which allows you to define rules for which Pods can be co-located on a node.

The affinity feature consists of two types of affinity:

    * Node affinity functions like the nodeSelector field but is more expressive and allows you to specify soft rules.
    * Inter-pod affinity/anti-affinity allows you to constrain Pods against labels on other Pods.

## Taints and Tolerations

Taint (зараза, испорченность) - применяется на node-ы, помечая их, чтобы те могли "отталкивать" pod-ы, без необходимых Tolerations.
Tolerations (терпимость) - применяется к pod-ам, чтобы те могли размещаться на нодах, имеющих совпадающие taint-/пометки.

Node affinity is a property of Pods that attracts them to a set of nodes (either as a preference or a hard requirement). Taints are the opposite -- they allow a node to repel a set of pods.

Tolerations are applied to pods. Tolerations allow the scheduler to schedule pods with matching taints. Tolerations allow scheduling but don't guarantee scheduling: the scheduler also evaluates other parameters as part of its function.

Taints and tolerations work together to ensure that pods are not scheduled onto inappropriate nodes. One or more taints are applied to a node; this marks that the node should not accept any pods that do not tolerate the taints.

### DaemonSet | Задание с **

Соответственно, так как на мастер-нодах установлен taint, который ограничивает размещение подов:
```
k describe nodes kind-control-plane | grep -i taints
Taints:             node-role.kubernetes.io/control-plane:NoSchedule
```
То необходимо pod-у, который мы всё же хотим разместить на такой ноде прописать соответствующий  toleration - тогда pod сможет быть размещён.

```
kind: DaemonSet
spec:
  template:
    spec:
      tolerations:
      - key: node-role.kubernetes.io/control-plane
        effect: NoSchedule
```