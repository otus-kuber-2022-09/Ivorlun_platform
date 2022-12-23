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

### Resource units in Kubernetes
Note: If you specify a limit for a resource, but do not specify any request, and no admission-time mechanism has applied a default request for that resource, then Kubernetes copies the limit you specified and uses it as the requested value for the resource.

There are limits also for PID count for POD to consume, storage and so on - https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/.
#### CPU resource units

Limits and requests for CPU resources are measured in cpu units. In Kubernetes, 1 CPU unit is equivalent to 1 physical CPU core, or 1 virtual core, depending on whether the node is a physical host or a virtual machine running inside a physical machine.

Fractional requests are allowed. When you define a container with spec.containers[].resources.requests.cpu set to 0.5, you are requesting half as much CPU time compared to if you asked for 1.0 CPU. For CPU resource units, the quantity expression 0.1 is equivalent to the expression 100m, which can be read as "one hundred millicpu". Some people say "one hundred millicores", and this is understood to mean the same thing.

#### Memory resource units

Limits and requests for memory are measured in bytes. You can express memory as a plain integer or as a fixed-point number using one of these quantity suffixes: E, P, T, G, M, k. You can also use the power-of-two equivalents: Ei, Pi, Ti, Gi, Mi, Ki. For example, the following represent roughly the same value: `128974848, 129e6, 129M,  128974848000m, 123Mi`

Pay attention to the case of the suffixes. If you request 400m of memory, this is a request for 0.4 bytes. Someone who types that probably meant to ask for 400 mebibytes (400Mi) or 400 megabytes (400M).

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

* **Liveness** - Жив ли контейнер или же нужно его перезапустить. Например приложение запущено, но зависло. Можно ловить в выводе дедблок, который об этом свидетельствует.
* **Readiness** - Готов ли контейнер полностью к работе, можно ли на него роутить трафик. Если под перестаёт быть готов, то его автоматом убирают из списка lb.
* **Startup** - задерживает предыдущие две, до тех пор пока его проверка не пройдёт. Нужно, чтобы другие probы не перезапустили контейнер пока приложение нормально не начнёт работу. Полезно для медленных приложений, БД и т.п..

Пока readinessProbe для нового pod не станет успешной - Deployment не будет пытаться продолжить обновление.
Чтобы отследить успешность деплоя можно использовать `kubectl rollout status deployment/frontend`

Описание pipeline, включающее в себя шаг развертывания и шаг отката, в самом простом случае может выглядеть так (синтаксис GitLab CI):
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
A DaemonSet ensures that all (or some) Nodes run a copy of a Pod. As nodes are added to the cluster, Pods are added to them. As nodes are removed from the cluster, those Pods are garbage collected.

Типичные кейсы использования DaemonSet:
* Сетевые плагины;
* Утилиты для сбора и отправки логов (Fluent Bit, Fluentd, etc…);
* Различные утилиты для мониторинга (Node Exporter, etc…);
## nodeSelector

nodeSelector is the simplest recommended form of node selection constraint. You can add the nodeSelector field to your Pod specification and specify the node labels you want the target node to have. Kubernetes only schedules the Pod onto nodes that have each of the labels you specify.

## Affinity and anti-affinity

**nodeSelector** is the simplest way to constrain Pods to nodes with specific labels. Affinity and anti-affinity expands the types of constraints you can define. Some of the benefits of affinity and anti-affinity include:

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

## Pod lifecycle
1. Подготовка и валидация runtime-объекта
1. Идентификация и авторизация запроса
1. Обработка запроса Admission Controllers
1. Сохранение ресурса в etcd
1. Основной цикл обработки ресурсов (e.g. Deployment Controller)
1. Запуск планировщика
1. Магия kubelet 🦄
1. Магия runtime. Подготовка изолированного окружения
1. Магия runtime. Инициализация сети
1. Магия runtime. Запуск контейнеров
1. И снова kubelet ... Запуск хуков


## AAA refers to Authentication (to identify), Authorization (to give permission) and Accounting (to log an audit trail)
После идентификации пользователя на kube-apiserver начинается самое интересное
1. Запрос проходит через цепочку Authorizers (RBAC, ABAC, Node):
  * Достаточно первого ответа (можно/нельзя)
  * Если ни один авторизатор не ответил внятно, запрос отклоняется
1. Далее, вызываются Admission Controllers, которые смотрят на параметры runtime-объекта
  * Можно/нельзя (e.g. PodSecurityPolicy)
  * Меняют параметры объекта (e.g. AlwaysPullImages )
  * Создают новые объекты (e.g. NamespaceAutoProvision)

## Kube-Scheduler (Планирование ресурсов)
1. Допущенные к запуску и окончательно мутировавшие Podы попадают в очередь планировщика
1. Планировщик ( kube-scheduler ) сортирует очередь
1. После сортировки планировщик выбирает ноды, подходящие для запуска Pod и делает оценку "пригодности" каждой ноды
1. В финале, происходит binding - привязка Poda к узлу (и измененный объект Pod сохраняется в etcd)


## Kubelet
1. kubelet опрашивает kube-apiserver и забирает список подов со своим NodeName
1. Полученный список подов сверяется со списком запущенных
1. Далее он удаляет и создает Podы, чтобы достичь соответствия между описанным и текущим состоянием.
1. NodeAuthorizer ограничивает права kubelet объектами, связанными с его Podами.
1. kubelet регистрирует базовые метрики связанные с Pod (например, тайминги запуска)
1. kubelet выполняет дополнительные проверки ( AdmissionHandlers ) для полученного Pod

#### Kubelet | AdmissionHandlers, PodSyncHandlers
1. Проверки Podа на совместимость с текущей версией и конфигурацией Runtime
  * NoNewPrivileges, sysctl, AppArmor/SELinux профили
1. Доступные ресурсы
* Для подов с гарантированными ресурсами всегда "зеленый свет" 🚦(ресурсы освобождаются потом)
1. Также kubelet делает периодические проверки запущенных Podов (начиная с момента запуска)
  * Например, проверка соответствия ActiveDeadline для Jobs
  * Podы не прошедшие проверку идут на... eviction
Проще говоря, Podы, которые прошли Server Dry-run, AdmissionController-ы и планировщик НЕ ОБЯЗАТЕЛЬНО будут запущены.

kubelet может опрашивать состояние контейнеров в поде. Для этого можно задать probes: livenessProbe, readinessProbe, startupProbe (он позволяет отложить выполнение других проверок, если первый запуск приложения занимает значительное время)


## Pod Pending > Running
Пока Pod висит в статусе Pending kubelet делает следующее:
1. Создает cgroups и настраивает ограничения ресурсов
1. Создает служебные папки для Podа
1. Подключает дисковые тома внутрь папки volumes
1. Получает реквизиты ImagePullSecrets
1. И наконец-то переходит к запуску контейенеров...
1. kubelet отправляет CRI-плагину запрос RunPodSandbox:
  * в случае с VM-плагинами, создается виртуальная машина
  * в случае с контейнерами, запускается тот-самый-pause-container и создаются namespace
1. Когда песочница создана, CRI вызывает сетевой плагин (CNI) и просит его инициализировать сетевое подключение
1. Наконец-то kubelet может позапускать контейнеры...
1. Но сначала запускаются Init-контейнеры. Зачем?
  * Для проверки внешних условий запуска контейнера ("Монго ли меня?", "Одинок ли я в этом кластере?")
  * Для предварительной конфигурации и загрузки данных (быстрая копия данных с реплики)
  * Чтобы не выдавать основному контейнеру лишние секреты
1. Теперь запускаем основные контейнеры, описанные в PodSpec
  * И в то же время запускается Post-Start Hook

## Pause-container
* Нужен, чтобы зарезервировать Kernel Namespace и сетевую конфигурацию для Pod
* Умеет убивать zombie-процессы. Но уже не надо:
  * Docker/Moby автоматом запускают tini init (https://github.com/krallin/tini)
  * Shared PID Namespace для пода сначала был включен, а теперь снова выключен (т.к. несекьюрно)
* Потребление памяти - примерно 180 байт.

# Homework 4 (Networks)

## Service
Виды сервисов
* ClusterIP (+ Headless service `clusterIP: None`)
* NodePort
* LoadBalancer
* ExternalName

## Service ExternalName
Services of type ExternalName map a Service to a DNS name, not to a typical selector such as my-service or cassandra. You specify these Services with the spec.externalName parameter.
```
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: prod
spec:
  type: ExternalName
  externalName: my.database.example.com
```
Note: ExternalName accepts an IPv4 address string, but as a DNS name comprised of digits, not as an IP address. ExternalNames that resemble IPv4 addresses are not resolved by CoreDNS or ingress-nginx because ExternalName is intended to specify a canonical DNS name. To hardcode an IP address, consider using headless Services.

When looking up the host my-service.prod.svc.cluster.local, the cluster DNS Service returns a CNAME record with the value my.database.example.com.

## **Local link**
169.254/16 - local link подсеть: Всё что попадает в эту подсеть никогда не выйдет за пределы этой подсети.
## Node local DNS cache
10.0.0.10 - cluster.local

Нужен для скорости и добавляет немного надёжности. Но имеет смысл только для большого количества RPS - иначе просто лишняя сущность.
Обычно отсутствует в инсталляциях для небольших кластеров.

В pod-е будет в /etc/resolv.conf c адресом из подсети `nameserver 169.254/16`

На каждой ноде, где развёрнут node local dns, запрос изначально уходит в него, а дальше уже происходит форворд на ClusterIP KubeDNS, если случился cache miss.

Если что-то находится за NAT-ом, отправляемые запросы могут терятся по UDP.
DNS request запрашивает upgrade force to TCP, чтобы не потерялся запрос от Node local DNS to KubeDNS.

Параметры адресов резолверов clusterDNS и домена кластера clusterDomain берутся из конфигов kubelet.

Можно прямо в самом spec pod-а менять параметры dns - есть секция dnsConfig.


### Upgrade UDP > TCP localDNS

В localDNS, который располагается на ноде и кеширует соответствие, используется upgrade to tcp (from udp), чтобы располагаясь за NATом запросы не терялись.

### Внутри кластера возможно обращение по следующим именам
* Обращение к сервису внутри namespace: service
* Обращение к сервису внутри кластера: service.namespace
* FQDN сервиса: service.namespace.svc.<домен кластера>.
* FQDN пода: 10-0-0-1.ns.pod.cluster.local** (Deprecated, но пока работает)

### Resolv.conf and ndots problem
По умолчанию, в resolv.conf добавляется опция options ndots:5
```
nameserver 10.96.0.10
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```
Это значит, что DNS-запросы, где меньше 5 точек (или не FQDN) обрабатываются так:
1. дописываем домен из списка search и пробуем резолвить
1. если не вышло,берем следующий домен,снова пробуем. Обычно, список такой: `default.svc.cluster.local svc.cluster.local cluster.local`

То есть ты делаешь резолв vk.com, а кубер тебе предлагает сначала:
1. vk.com.default.svc.cluster.local
2. vk.com.svc.cluster.local
3. vk.com.cluster.local
4. Только тут идёт на внешний резолвер

**!** По идее добавление точки в конце сделает из любого адреса FQDN - тогда она минует search директиву из resolv.conf и сразу пойдёт запрашивать адрес вовне, минуя поиск.

При ndots 5 часто бывают задержки и проще выставлять `options ndots:1`

### Musl (Apline) vs libc
Alpine часто используется в роли базового образа в Kubernetes
А там вместо glibc с ее кучей известных особенностей применяется musl
libc

One common issue you may find is with DNS. musl libc does not use domain or search directives in the /etc/resolv.conf file.
https://github.com/gliderlabs/docker-alpine/blob/master/docs/caveats.md


### Kubernetes DNS-Based Service Discovery
https://github.com/kubernetes/dns/blob/master/docs/specification.md


## Masquerading and NAT
Важно помнить разницу между MASQ и NAT
* Маскарад - замена адреса на адрес машины, выполняющей маскарад.
* Трансляция адресов - замена адреса на любой указанный.

## Cluster IP
Каждый Pod имеет свой собственный IP
При пересоздании (может быть очень часто) Pod-а IP меняется.

Сервис
* имеет постоянный IP
* обеспечивает балансировку
* облегчает взаимодействие внутри и вне кластера

Когда создаём сервис, то на каждой ноде kube-proxy создаёт правила iptables (или ipvs).

Проще один раз увидеть - пример для сервиса из 3х эндпонитов.

Если запрос пришёл на ip, то отправь его в цепочку: `KUBE-SERVICES -d 10.104.92.240/32`, где с 33% полетит дальше по цепочке или же осядет в поде с ip, а если полетел дальше, то с 50% осядет в одном из следующих подов.

```
$ kubectl get svc
NAME        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
my-service  ClusterIP   10.104.92.240   <none>        80/TCP    5h43m

$ iptables-save | grep "my-service"
-A KUBE-SEP-74M76R3MOH5BJ7FU -s 10.0.2.51/32 -m comment --comment "default/my-service" -j KUBE-MARK-MASQ
-A KUBE-SEP-74M76R3MOH5BJ7FU -p tcp -m comment --comment "default/my-service" -m tcp -j DNAT --to-destination 10.0.2.51:9376
-A KUBE-SEP-JPAADZTWUNYJQEJV -s 10.0.1.30/32 -m comment --comment "default/my-service" -j KUBE-MARK-MASQ
-A KUBE-SEP-JPAADZTWUNYJQEJV -p tcp -m comment --comment "default/my-service" -m tcp -j DNAT --to-destination 10.0.1.30:9376
-A KUBE-SEP-KVEHKWBOWX3KCL2I -s 10.0.2.167/32 -m comment --comment "default/my-service" -j KUBE-MARK-MASQ
-A KUBE-SEP-KVEHKWBOWX3KCL2I -p tcp -m comment --comment "default/my-service" -m tcp -j DNAT --to-destination 10.0.2.167:9376
-A KUBE-SERVICES -d 10.104.92.240/32 -p tcp -m comment --comment "default/my-service cluster IP" -m tcp --dport 80 -j KUBE-SVC-FXIYY6OHUSNBITIX
-A KUBE-SVC-FXIYY6OHUSNBITIX -m comment --comment "default/my-service" -m statistic --mode random --probability 0.33333333349 -j KUBE-SEP-JPAADZTWUNYJQEJV
-A KUBE-SVC-FXIYY6OHUSNBITIX -m comment --comment "default/my-service" -m statistic --mode random --probability 0.50000000000 -j KUBE-SEP-KVEHKWBOWX3KCL2I
-A KUBE-SVC-FXIYY6OHUSNBITIX -m comment --comment "default/my-service" -j KUBE-SEP-74M76R3MOH5BJ7FU
```

Вроде как cilium умеет это делать без iptables kube-proxy


## Headless service
clusterIP: None
Работает только как DNS запись - запрашиваешь его адрес, а в ответ получаешь список эндпонитов.

## NodePort
* На каждой ноде открывается один и тот же порт из особого диапазона
* Который делает DNAT на адреса Pods

## LoadBalancer
* Этот вид сервиса предназначен только для облачных провайдеров, которые своими программными средствами реализуют балансировку нагрузки.
* В Bare Metal это делается чуть иначе - используется MetalLB

## Ingress
Объект управляющий внешним доступом к сервисам внутри кластера, по факту набор правил внутри кластера Kubernetes.
Обеспечивает:
* Организацию единой точки входа в приложения снаружи
* Балансировку трафика
* Терминацию SSL
* Виртуальный хостинг на основе имен и т.д.
* Работает на L7 уровне.

Для применения данных правил нужен Ingress Controller - плагин
который состоит из 2-х функциональных частей:
1. Приложение, которое отслеживает через Kubernetes API новые объекты
Ingress и обновляет конфигурацию балансировщика
2. Сам балансировщик (nginx,HAProxy, traefik, …),который отвечает за
управление сетевым трафиком

#### Типичные виды Ingress

* Single Service Ingress - один ингресс целиком для одного сервиса
* Simple Fanout - делим трафик по сервисам в зависимости от пути контекста
* Name Based Virtual Hosting - делим трафик по сервисам в зависимости от доменного имени
* TLS termination - вешаем tls на ingress, а внутренний трафик без сертификата

## TLS termination

**Client** <--https--> **Proxy** <--http--> **Application**

Механизм, при котором запросы снаружи до reverse-proxy идут как обычно шифрованные, но уже от reverse-proxy до приложения идут без шифрования трафика. То есть шифрование "уничтожается" при достижении proxy.

Это позволяет разгрузить сервер приложения и оставить эту работу reverse-proxy севрверу.
Также, если прокся дешифрует трафик, то она начинает понимать его содержимое, а значит, может баланисровать, кешировать и тп

* Offloads main server crytpo
* TLS closer to client
* HTTP accelerators (Varnish)
* Intrusion detection systems - если тебя атакуют проще сниффить трафик после дешифровки
* Load balancing/Service mesh


В случае kubernetes это легко можно осуществлять с помощью ingress.

## TLS Forward Proxy
Но так же есть ещё и фокус сделать TLS forward proxy.

Суть в том, что происходит то же TLS termination, только трафик уже шифруется между Proxy и бэкендом своим собственным ключом после его дешифровки проксёй.

**Client** <----https encr1----> **Proxy** <----https encr2----> **Application**

Это, с одной стороны позволяет дешифровывать трафик и управлять им - балансировать и кешировать, с другой, устраняет незащищённый канал между бэком и проксёй. Нагрузка по шифровке на бэкенде присутствует.
Часто для этого используют **Varnish**.


### Настройки из практики использования
`hostNetwork: true`

В таком случае **сетевой Namespace не создается**. Pod напрямую видит сетевые адаптеры ноды.

Так работают Pod, которые реализуют сетевую подсистему, например, никто не мешает сделать так Ingress Pod c ingress-nginx


`hostPort для контейнера`

Можно указать для контейнера порт, который будет открыт на ноде.
На ноде,где в итоге оказался Pod одновременно так не могут делать несколько контейнеров по понятной причине.
Опять же,для Ingress Pod почему бы и нет.


`externalIP для Service`

Можно указать конкретные внешние сетевые адреса для сервиса - тогда в iptables будут созданы необходимые правила и пробросы внутрь.

## Kube-proxy vs CNIs (Calico and etc.)

### CNI cares about Pod IP.

CNI Plugin is focusing on building up an overlay network, without which Pods can't communicate with each other. The task of the CNI plugin is to assign Pod IP to the Pod when it's scheduled, and to build a virtual device for this IP, and make this IP accessable from every node of the cluster.

### kube-proxy

kube-proxy's job is rather simple, it just redirect requests from Cluster IP to Pod IP.
kube-proxy has two mode, IPVS and iptables.
https://stackoverflow.com/a/54881661


Kube-proxy process handles everything related to Services on each node. It ensures that connections to the service cluster IP and port go to a pod that backs the service. If backed by more than one service, kube-proxy load-balances traffic across pods.
https://docs.projectcalico.org/networking/use-ipvs
Calico gives you a choice of dataplanes, including a pure Linux eBPF dataplane, a standard Linux networking dataplane, and a Windows HNS dataplane.

## Homework part
#### Осмысленность ps aux probe
Полагаю, что причина по которой конфигурация вида
```
livenessProbe:
  exec:
    command:
      - 'sh'
      - '-c'
      - 'ps aux | grep my_web_server_process'
```
бессмысленна в том, что liveness определяет нужно ли перезапуситить контейнер, например из-за зависания приложения. А с учётом того, что процесс приложения вунтри контейнера как правило является основным и, соотвтественно, если контейнер запущен, то существует - описанный подход не поможет определить его истинную работоспособность, а проверка всегда будет успешно проходить.
Но, скорее всего, имеет некоторый смысл для приложений у которых pid 1 - init, а целевой процесс будет дочерним.

## SCTP
SCTP (англ. Stream Control Transmission Protocol — «протокол передачи с управлением потоком») — протокол транспортного уровня в компьютерных сетях, появившийся в 2000 году.

Как и любой другой протокол передачи данных транспортного уровня, SCTP работает аналогично TCP или UDP. Будучи более новым протоколом, SCTP имеет несколько нововведений, таких как многопоточность, защита от DDoS-атак, синхронное соединение между двумя хостами по двум и более независимым физическим каналам (multi-homing). TCP понятие «соединение» означает обмен данными между двумя точками, в то время как в SCTP имеет место концепция «ассоциации» (англ. association), обозначающая всё происходящее между двумя узлами. Например, можно быть соединённым одновременно по wifi и eth. Недостаток - бОльшая занимаемая полоса.

### Вызов kube-proxy как бинаря

Можно делать прямо так `k -n kube-system exec kube-proxy-h8nlf  -- kube-proxy --help`.
Здесь можно увидеть какие возомжности есть у kube-proxy как логической единицы.

The Kubernetes network proxy runs on each node. This reflects services as defined in the Kubernetes API on each node and can do simple TCP, UDP, and SCTP stream forwarding or round robin TCP, UDP, and SCTP forwarding across a set of backends. Service cluster IPs and ports are currently found through Docker-links-compatible environment variables specifying ports opened by the service proxy. There is an optional addon that provides cluster DNS for these cluster IPs. The user must create a service with the apiserver API to configure the proxy.

Например, можно вызывать cleanup: `kube-proxy --cleanup   If true cleanup iptables and ipvs rules and exit.`

Во-первых, даёт понимание как же всё-таки работает kubernetes на низком уровне.
Во-вторых, позволяет отлаживаться или тестировать более гибко.
## Kubectl top
В некоторых контейнерах отсутствую утилиты для наблюдения за процессами, а также, установщики пакетов (Debian):
`OCI runtime exec failed: exec failed: unable to start container process: exec: "apt-get": executable file not found in $PATH: unknown`
Чтобы не заморачиваться в kuber-е существует аналог `docker top`: `kubectl top`, который позволяет смотреть процессы не только pod-а, но и целой node-ы.

Но для этого необходим установленный в кластере компонент metrics-server.
В minikube решается: `minikube addons enable metrics-server`

## iptables-restore из файла

Можно создавать правила для iptables в виде файла и загружать их из файла, переписывая текущие:
Для примера, создадим в ВМ с Minikube файл /tmp/iptables.cleanup
```
*nat
-A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE
COMMIT
*filter
COMMIT
*mangle
COMMIT
```
и все правила удаляются: `iptables-restore /tmp/iptables.cleanup`.
А дальше kube-proxy заново их восстанавливает, так как kube-proxy периодически делает полную синхронизацию правил в своих цепочках.
**iptables --list -nv -t nat**

### ClusterIP

ClusterIP удобны в тех случаях, когда:
* Нам не надо подключаться к конкретному поду сервиса
* Нас устраивается случайное расределение подключений между подами
* Нам нужна стабильная точка подключения к сервису, независимая от подов, нод и DNS-имен
Например:
* Подключения клиентов к кластеру БД (multi-read) или хранилищу
* Простейшая (не совсем, use IPVS, Luke) балансировка нагрузки внутри кластера

В каждом неймспейсе есть ClusterIP, который предоставляет доступ к api-server-у всем компонентам namespace-а. **Кто его запускает?**
```
Name:              kubernetes
Namespace:         default
Labels:            component=apiserver
                   provider=kubernetes
```

* ClusterIP выделяет IP-адрес для каждого сервиса из особого диапазона (этот адрес виртуален и даже не настраивается на сетевых интерфейсах)
* Когда pod внутри кластера пытается подключиться к виртуальному IP-адресу сервиса, то node, где запущен pod, меняет адрес получателя в сетевых пакетах на настоящий адрес pod-а.
* Нигде в сети, за пределами ноды, виртуальный ClusterIP не существует.

Every node in a Kubernetes cluster runs a kube-proxy. kube-proxy is responsible for implementing a form of virtual IP for Services of type other than ExternalName.

То есть это функционал типа dnat, который заменяет виртуальный ip ClusterIP > Target Pod IP.
Соответственно с физических нод этот IP не должен пинговаться - он хранится только в цепочках iptables.

Получается, что **при использовании IPtables**, IP-адрес сервиса ClusterIP создаётся и существует только в базе etcd, откуда он подтягивается kube-proxy, уже который создаёт для этого несуществующего виртуального адреса правила маршрутизации на конкретном хосте.
На каждом хосте kube-proxy подменяет адрес и пишет: если ты обращаешься по этому адресу, то вот тебе подменённый настоящий адрес куда тебе нужно.
Эти правила куб прокси постоянно синхронизирует с кластером.

Вот адрес сервиса 10.102.189.119:
```
iptables --list -nv -t nat
 pkts bytes target     prot opt in     out     source               destination
    1    60 KUBE-MARK-MASQ  tcp  --  *      *      !10.244.0.0/16        10.102.189.119       /* default/web-svc-cip cluster IP */ tcp dpt:80
    1    60 KUBE-SVC-6CZTMAROCN3AQODZ  tcp  --  *      *       0.0.0.0/0            10.102.189.119       /* default/web-svc-cip cluster IP */ tcp dpt:80

```
Вот балансировка между 3мя enpoint-ами:
```
Chain KUBE-SVC-6CZTMAROCN3AQODZ (1 references)
 pkts bytes target     prot opt in     out     source               destination
    0     0 KUBE-SEP-SLOPQOZW34M3DWKM  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* default/web-svc-cip */ statistic mode random probability 0.33333333349
    1    60 KUBE-SEP-JXVMOJ4WLIQT6I2K  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* default/web-svc-cip */ statistic mode random probability 0.50000000000
    0     0 KUBE-SEP-HA42FWOOMUOBT5YR  all  --  *      *       0.0.0.0/0            0.0.0.0/0            /* default/web-svc-cip */

```
Где **SEP** - Service Endpoint

**Но!**
## IPVS vs IPtables
**В случае работы через ipvs, а не iptables, clusterIP записывается на сетевой интерфейс** и перестаёт быть виртуальным адресом и его можно пинговать!
При этом правила в **IPVS** построены по-другому. Вместо цепочек правил для каждого сервиса и каждого пода, теперь используются хэш-таблицы (**ipset**). HashMap-ы составляются для типов сервисов и состоят из пары ip+port. Можно их посмотреть, установив утилиту **ipvsadm** или ipset.

То есть при работе через IPVS внутри iptables хранится необходимый минимум для работы, а основная информация по маршрутам - в быстрых хэш-таблицах, которые как раз хорошо работают при большом количестве нод.
IPVS proxier will employ IPTABLES in doing packet filtering, SNAT or masquerade. Specifically, IPVS proxier will use ipset to store source or destination address of traffics that need DROP or do masquerade, to make sure the number of IPTABLES rules be constant, no matter how many services we have.
https://github.com/kubernetes/kubernetes/blob/master/pkg/proxy/ipvs/README.md

Более подробно - ниже. `ipset list` для всех CLUSTER-IP:
```
Name: KUBE-CLUSTER-IP
Type: hash:ip,port
Revision: 5
Header: family inet hashsize 1024 maxelem 65536
Size in memory: 584
References: 2
Number of entries: 8
Members:
10.96.0.10,tcp:53
10.96.0.1,tcp:443
10.102.189.119,tcp:80
10.100.169.199,tcp:80
10.100.114.194,tcp:8000
10.100.124.99,tcp:80
10.96.0.10,tcp:9153
10.96.0.10,udp:53
```

## IPVS
IPVS (IP Virtual Server) implements **transport-layer load balancing**, usually called Layer 4 LAN switching, as part of Linux kernel.

IPVS runs on a host and acts as a load balancer in front of a cluster of real servers. IPVS can direct requests for TCP and UDP-based services to the real servers, and make services of real servers appear as virtual services on a single IP address.

**Разница в балансировке сервисов между iptables и ipvs** следующая. Допустим 3 пода, на которые может уходить трафик с сервиса:
* iptables: последовательная цепочка правил 0.33 * ip pod1 > 0.5 * pod2 > pod3 - эти вероятности выбора пода динамически изменяются в зависимости от масштабирования. Добавили под - изменили все вероятности.
* ipvs: изначально балансировщик и в него вшит менее топорный механизм балансировки (least load, least connections, locality, weighted, etc. http://www.linuxvirtualserver.org/docs/scheduling.html) и достаточно добавить ip нового пода в соответствие к адресу, а не обновлять правила целиком каждый раз, меняя вероятности.

Вместо цепочки правил для каждого сервиса, теперь используются хэш-таблицы (ipset). Можно посмотреть их используя `ipvsadm --list --numeric` (`ipvsadm -Ln`)

Вот так выглядит Round Robin балансировка для адресации сервиса на поды:
```
Prot LocalAddress:Port Scheduler Flags
  -> RemoteAddress:Port           Forward Weight ActiveConn InActConn

TCP  10.99.69.111:80 rr
  -> 172.17.0.3:8000              Masq    1      0          0
  -> 172.17.0.4:8000              Masq    1      0          0
  -> 172.17.0.5:8000              Masq    1      0          0
```


При этом для баланисировщика создаётся виртуальный сетевой интерфейс, на котором будут все адреса сервисов. Здесь **kube-ipvs0**:
```
kube-ipvs0: <BROADCAST,NOARP> mtu 1500 qdisc noop state DOWN group default
    link/ether 2e:f7:f3:b2:35:a4 brd ff:ff:ff:ff:ff:ff
    inet 10.102.189.119/32 scope global kube-ipvs0
       valid_lft forever preferred_lft forever
    inet 10.100.124.99/32 scope global kube-ipvs0
       valid_lft forever preferred_lft forever
    inet 10.100.114.194/32 scope global kube-ipvs0
       valid_lft forever preferred_lft forever
    inet 10.96.0.1/32 scope global kube-ipvs0
       valid_lft forever preferred_lft forever
    inet 10.96.0.10/32 scope global kube-ipvs0
       valid_lft forever preferred_lft forever
```
## DNS Debug handbook
https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/

### Проблема DNS, с которой столкнулся во время домашки iptables > ipvs.

Если менять kube-proxy mode на ipvs "на горячую", то возникает проблема с тем, что правила iptables не стираются даже после удаления pod kube-proxy. В домашке предлагается полная очистка правил на уровне самого контейнера minikube через iptables-restore. **Но** в качестве DNS-резолвера в `/etc/resolv.conf` minikube указан 192.168.49.1:53 - то есть IP-адрес хоста на котором развёрнут уже сам minikube. Сейчас minikube почти везде разворачивается через docker-in-docker, соответственно очистка всех правил приводит к тому, что DNS во всём кластере и в самом контейнере minikube перестаёт работать.

После того как kube-proxy переводится в режим ipvs, а в контейнере minikube очищаются цепочки правил через iptables-restore из пустого файла, то, при синхронизации kube-proxy цепочек в хэшмапы ipvs:
1. Правила и цепочки, которые были свзяаны с выходом на DNS основного хоста 192.168.49.1:53 стираются из iptables из-за iptables-restore.
1. Восстанавливаются правила только для kubernetes, но не для docker bridge-а.
1. В `/etc/resolv.conf` самого хоста куба сохраняется запись `nameserver 192.168.49.1`
1. Все DNS-запросы изнутри кластера уходят на ClusterIP kube-dns, который отправляет их наружу  minikube, где они и застревают, так как за его пределы выйти уже не могут.

**В итоге я сделал следующую команду для сохранения цепочек моста**:
`iptables-save | grep -E '192.168.|docker0|DOCKER|\*|COMMIT' > /tmp/iptables.cleanup`

После чего получился следующий дамп правил:
```
*nat
:DOCKER_OUTPUT - [0:0]
:DOCKER_POSTROUTING - [0:0]
:DOCKER - [0:0]
-A PREROUTING -d 192.168.49.1/32 -j DOCKER_OUTPUT
-A PREROUTING -m addrtype --dst-type LOCAL -j DOCKER
-A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE
-A POSTROUTING -d 192.168.49.1/32 -j DOCKER_POSTROUTING
-A OUTPUT -d 192.168.49.1/32 -j DOCKER_OUTPUT
-A OUTPUT ! -d 127.0.0.0/8 -m addrtype --dst-type LOCAL -j DOCKER
-A DOCKER_OUTPUT -d 192.168.49.1/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 127.0.0.11:46227
-A DOCKER_OUTPUT -d 192.168.49.1/32 -p udp -m udp --dport 53 -j DNAT --to-destination 127.0.0.11:37174
-A DOCKER_POSTROUTING -s 127.0.0.11/32 -p tcp -m tcp --sport 46227 -j SNAT --to-source 192.168.49.1:53
-A DOCKER_POSTROUTING -s 127.0.0.11/32 -p udp -m udp --sport 37174 -j SNAT --to-source 192.168.49.1:53
-A DOCKER -i docker0 -j RETURN
COMMIT
*filter
:DOCKER - [0:0]
:DOCKER-ISOLATION-STAGE-1 - [0:0]
:DOCKER-USER - [0:0]
:DOCKER-ISOLATION-STAGE-2 - [0:0]
-A FORWARD -j DOCKER-USER
-A FORWARD -j DOCKER-ISOLATION-STAGE-1
-A FORWARD -o docker0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A FORWARD -o docker0 -j DOCKER
-A FORWARD -i docker0 ! -o docker0 -j ACCEPT
-A FORWARD -i docker0 -o docker0 -j ACCEPT
-A DOCKER-ISOLATION-STAGE-1 -i docker0 ! -o docker0 -j DOCKER-ISOLATION-STAGE-2
-A DOCKER-ISOLATION-STAGE-1 -j RETURN
-A DOCKER-USER -j RETURN
-A DOCKER-ISOLATION-STAGE-2 -o docker0 -j DROP
-A DOCKER-ISOLATION-STAGE-2 -j RETURN
COMMIT
*mangle
COMMIT
```
Из которого уже делал `iptables-restore /tmp/iptables.cleanup`.

Это позволяет обойти проблему с нерабочей сетью в minikube и необходимостью прописывать nameserver-ы в /etc/resolv.conf или изменять cm coredns upstreamnameservers https://kubernetes.io/docs/tasks/administer-cluster/dns-custom-nameservers/.

Это супер большая проблема так как из-за неё нельзя ничего задеплоить в кластер, любая загрузка из интернета ломается.
Встречалась не только у меня - https://otus-devops.slack.com/archives/C04139FTKC5/p1666525079135599.

## Forwarding Information Base trie (Aka FIB trie)

Префиксное дерево, которое используется при хранении префиксов ip-адресов внутри маршрутов и мостов. Compressed variants of tries, such as databases for managing Forwarding Information Base (FIB), are used in storing IP address prefixes within routers and bridges for prefix-based lookup to resolve mask-based operations in IP routing.

IPv4 Routing Subsystem, in specifically the Forwarding Information Base trie (Aka FIB trie). The FIB trie is the main data structure used by the IPv4, it defines the routing trie and can be used by us to collect our IP addresses, gateway IP, netmask, etc.
https://medium.com/bash-tips-and-tricks/getting-the-linux-ip-address-without-any-package-ifconfig-ip-address-etc-7b1363077964
cat /proc/net/fib_trie

**Trie** - In computer science, a trie, also called digital tree or **prefix** tree, is a type of k-ary search tree, a tree data structure used for locating specific keys from within a set.
Префиксное дерево — структура данных, позволяющая хранить ассоциативный массив, ключами которого являются строки. Представляет собой корневое дерево (В теории графов корневым графом называется граф, в котором одна вершина помечена, чтобы отличать её от других вершин. Эту специальную вершину называют корнем графа), каждое ребро которого помечено каким-то символом так, что для любого узла все рёбра, соединяющие этот узел с его сыновьями, помечены разными символами.
(https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%B5%D1%84%D0%B8%D0%BA%D1%81%D0%BD%D0%BE%D0%B5_%D0%B4%D0%B5%D1%80%D0%B5%D0%B2%D0%BE)

T
├── e (Te)
│   ├── ch (Tech)
│   ├── ea  (Tea)
│   │   └──  pot  (Teapot)
└── o (To)


# Lifehack to see diff and apply changes automatically
see what changes would be made, returns nonzero returncode if different

kubectl get configmap kube-proxy -n kube-system -o yaml | \
sed -e "s/strictARP: false/strictARP: true/" | \
kubectl diff -f - -n kube-system

actually apply the changes, returns nonzero returncode on errors only
kubectl get configmap kube-proxy -n kube-system -o yaml | \
sed -e "s/strictARP: false/strictARP: true/" | \
kubectl apply -f - -n kube-system


### MetalLB
Использую актуальную версию metallb (`kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.7/config/manifests/metallb-native.yaml`), так как в версии 1.25 куба нет PodSecurityPolicy: in the policy/v1beta1 API version is no longer served in v1.25, and the PodSecurityPolicy admission controller was removed.

Далее в связи с багом https://github.com/metallb/metallb/issues/1597 вебхука пришлось удалить под контроллера после развёртки всех объектов metallb - иначе он не мог подцепить сертификат.

После этого необходимо было заменить конфиг из домашки на новую версию конфига в виде CRD:
```
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default
  namespace: metallb-system
spec:
  addresses:
    - "172.17.255.1-172.17.255.255"
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default
  namespace: metallb-system
```
После чего был успешно присвоен внешний ip-адрес.
Комментарий на github - https://github.com/metallb/metallb/issues/1597#issuecomment-1340106498.

#### Share single ip for several services
By default, Services do not share IP addresses. If you have a need to colocate services on a single IP, you can enable selective IP sharing by adding the metallb.universe.tf/allow-shared-ip annotation to services.
```
  annotations:
    metallb.universe.tf/allow-shared-ip: "true"
```

## ARP ликбез
ARP (address resolution protocol) используется для конвертации IP в MAC, соответственно работает, условно, на L2-канальном уровне, но для L3-сетевого.
Для этого он отправляет на широковещательный адрес запрос, все участники подсети его получают, и нужный отправляет ответ.
Важно, что можно узнать MAC-и только подсети, так как работает ниже L3-сетевого уровня и, соответственно, за маршрутизатор не выходит.
При этом:
* Участники сети, получив ARP запрос могут сразу составлять свою таблицу, чтобы в дальнейшем знать куда отправлять трафик
* Можно генерить запрос Gratuitous ARP (добровольный запрос) собственного ip, который позволит:
    * оповестить других об изменении своего ip
    * проверить нет ли коллизий ip-адресов в сети

### Static routes to LB subnet

Если запустить металлб в миникубе, то с основной машины не получится достучаться до него.
Это потому, что сеть кластера изолирована от основной ОС (а ОС не знает ничего о подсети для балансировщиков).
Чтобы это поправить, добавим статический маршрут:
* В реальном окружении это решается добавлением нужной подсети на интерфейс сетевого оборудования
* Или использованием L3-режима (что потребует усилий от сетевиков, но более предпочтительно)

### Задание со ⭐️ | DNS через MetalLB

В документации MetalLB (v0.13.7) устаревшая информация:
> Kubernetes does not currently allow multiprotocol LoadBalancer services. This would normally make it impossible to run services like DNS, because they have to listen on both TCP and UDP. To work around this limitation of Kubernetes with MetalLB, create two services (one for TCP, one for UDP), both with the same pod selector. Then, give them the same sharing key and spec.loadBalancerIP to colocate the TCP and UDP serving ports on the same IP address.

На самом деле с версии 1.24 для сервисов типа LB можно использовать несколько протоколов (https://kubernetes.io/docs/concepts/services-networking/service/#load-balancers-with-mixed-protocol-types), более того -
фича включена по умолчанию и не нужно создавать 2 сервиса, которые бы объединялись с помощью аннотации `metallb.universe.tf/allow-shared-ip: "true"` как раньше.

`kube-system      service/dns-svc-lb        LoadBalancer   10.101.92.187   172.17.255.2   53:30821/TCP,53:30821/UDP`

Ответ с хоста после добавление маршрута до пула адресов LB через интерфейс minikube (sudo ip r add 172.17.255.0/24 via 192.168.49.2):

```
❯ nslookup kubernetes.default.svc.cluster.local 172.17.255.2
Server:		172.17.255.2
Address:	172.17.255.2#53

Name:	kubernetes.default.svc.cluster.local
Address: 10.96.0.1
```

### Load balancers with mixed protocol types
The feature gate MixedProtocolLBService (enabled by default for the kube-apiserver as of v1.24) allows the use of different protocols for LoadBalancer type of Services, when there is more than one port defined.

https://kubernetes.io/docs/concepts/services-networking/service/#load-balancers-with-mixed-protocol-types

## Ingress
**ВСЕГДА! Указывать ingressClassName.**

If the ingressClassName is omitted, a default Ingress class should be defined.

В моём случае отсутствие привело к тому, что ингресс создавался некорректно и LoadBalancer Metallb отказался связывать LB с pod-ами ingress-а, для которых предназначался.
При этом у моего же ingress-а, оказалась следующая опция: Ingress-NGINX controller can be configured with a flag --watch-ingress-without-class.


Примеры работы с ингрессом и сервис для тестов

https://github.com/kubernetes/ingress-nginx/blob/main/docs/examples/index.md

#### service.spec.externalTrafficPolicy
externalTrafficPolicy denotes if this Service desires to route external traffic to node-local or cluster-wide endpoints.
* "Local" preserves the client source IP and avoids a second hop for LoadBalancer and Nodeport type services, but risks potentially imbalanced traffic spreading.
* "Cluster" obscures the client source IP and may cause a second hop to another node, but should have good overall load-spreading

By setting ExternalTrafficPolicy=local, nodes only route traffic to pods that are on the same node, which then preserves client IP (e.g., a browser or mobile application). It’s important to recognize that ExternalTrafficPolicy is not a way to preserve source IP; it’s a change in networking policy that happens to preserve source IP.


### Ingress headless service
Классная тема вязать ингресс на балансер
1. Создаём сервис типа LB, который балансирует 80 и 443 в namespace: ingress-nginx, перехватывая трафик pod-а ingress-контроллера, выбирая его по селектору
1. Создаём сервис типа ClusterIP, но без clusterIP! (clusterIP: None), который выбирает приложение по селектору https://kubernetes.io/docs/concepts/services-networking/service/#headless-services
1. Создаём ingress, который проксирует наше приложение, выбирая сервис ClusterIP по backend service name и port.

Из этого получится - единая точка входа, которая балансируется с полными возможностями metallb и openresty nginx-а.

То есть при MetalLB External IP + Ingress запрос извне проходит следующую цепочку:
1. Приходит на внешний ip-адрес MetalLB L4-балансировщика (externalTrafficPolicy: Local type:LoadBalancer)
1. Из балансировщика перенаправляется в nginx-ingress-controller pod, с которым LB связан по лейблам
1. Из ingress-а запрос уходит на нужный ClusterIP сервис, который указан в rules и backend-е ingress.yaml
1. Из ClusterIP сервиса уже попадает в целевые pod-ы


## Ephemeral Containers

Since Pods are just groups of semi-fused containers and the isolation between containers in a Pod is weakened, such a new container could be used to inspect the other containers in the (acting up) Pod regardless of their state and content.

And that's how we get to the idea of an Ephemeral Container - "a special type of container that runs temporarily in an existing Pod to accomplish user-initiated actions such as troubleshooting."

k debug -n <namespace> <pod-to-debug> --image=busybox

https://iximiuz.com/en/posts/kubernetes-ephemeral-containers/

## Debugging pods!

1. kubectl get (+ --watch or -w)
1. kubectl describe
1. kubectl get events
1. kubectl logs
1. kubectl exec -it <pod> -- sh (if possible)
1. kubectl debug -n <namespace> <pod-to-debug> --image=busybox
1. kubectl debug mypod -it --copy-to=my-debugger --image=debian --set-image=app=app:debug,sidecar=sidecar:debug (Which creates a copy of mypod adding a debug container and changing container images.)
1. kubectl debug node/mynode -it --image=ubuntu (Debugging via a shell on the node. Don't forget to clean up it.)

Also there are option to combine any way below:
* Debugging using a copy of the Pod
* Copying a Pod while adding a new container
* Copying a Pod while changing its command
* Copying a Pod while changing container images



https://github.com/kubernetes/dashboard/blob/v2.7.0/docs/user/access-control/creating-sample-user.md

Now we need to find the token we can use to log in. Execute the following command:

kubectl -n kubernetes-dashboard create token admin-user

Now copy the token and paste it into the Enter token field on the login screen.

### Ingress context path shift to root problem

При наличии в приложении basehref ресурсы неправильно маппятся и не дают открывать сайты.
https://github.com/kubernetes/ingress-nginx/issues/2557#issuecomment-619513010

Пробовал также через аннотацию `nginx.ingress.kubernetes.io/app-root: /dashboard/` и `spec.rules.http.paths.path: /dashboard/`, но это так же привело к ошибкам в js скриптах и относительных путях css дашборда:
```
# NOT WORKING!

  annotations:
    nginx.ingress.kubernetes.io/app-root: /dashboard/
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /dashboard/
```

Похоже, что ингресс nginx-а не должен переписывать / и сдвигать контекст: т.е. если ингресс имеет endpoint вида
https://ingress/dashboard/index.html, то он не может, просто убрав префикс, заммапить запрос в контейнер, в котором в location / лежит index.html и работает по урлу https://endpoint/index.html.

В общем получилось исправить следующей конфигурацией, наподобие примеру https://github.com/kubernetes/ingress-nginx/blob/controller-v1.6.0/docs/examples/rewrite/README.md:

```
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /dashboard(/|$)(.*)
```

### Kuber Dashboard context ingress
Дашборд к тосму же LB, но к другому ingress, чтобы не заниматься кросс-неймспейс проксированием.
Для дашборда потребовались аннотации:
```
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
```
**Чтобы не конфликтовать с другими сервисами** необходимо менять номер префикса запроса `rewrite-target: /$2` - т.е. на одном бэкенде $1, на другом - $2.

Captured groups are saved in numbered placeholders, chronologically, in the form $1, $2 ... $n. These placeholders can be used as parameters in the rewrite-target annotation.

## Deployment strategies
* Rollout (step-by-step workloads update)
* Canary Release (progressive traffic shifting e.g.:5%>10%>30%>100%)
* A/B Testing (HTTP headers and cookies traffic routing)
* Blue/Green (traffic switching)
* Blue/Green Mirroring (traffic shadowing)
* Canary Release with Session Affinity

Важно, что A/B тестирование так и называется, так как основной упор делает на исследовании гипотез и экспериментах, не являясь стратегией деплоя как таковой. Под капотом канарейка с остановкой.

То есть остальные стратегии имеют задачу развернуть новую версию приложения и ищут равновесие многих факторов, относясь больше к SRE, а A/B-тестирование больше тянет к аналитике.


https://docs.flagger.app/usage/deployment-strategies
## Canary Ingress и как взаимодействуют компоненты при использовании ingress и MetalLB
Важный момент, как это всё взаимодействует в конкретном примере и в принципе.

Существуют 2 deployment-а в namespace default:
* web - 3 replicas
* web-canary - 2 replicas

Существуют для каждого из них headless ClusterIP service-ы, которые по селектору `label=web` или `label=web-canary` выбирают на какую группу подов обращаться.
* web-svc
* web-canary-svc

Для того, чтобы сделать содержание их index.html доступным по контексту `/web/` (т.е. http://address/web/index.html) используются для каждого ingress-ы, то есть правила маршрутизации трафика извне, в данном случае, на сервисы ClusterIP.
* web
* web-canary

Причём, ingress canary включается только при наличии в запросе header-а `canary=forsure`:
```
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-by-header: "x-region"
    nginx.ingress.kubernetes.io/canary-by-header-value: "us-east"
```

Наконец, есть комбинация из L4-балансировщика с внешним IP, подов ингресс-контроллера, привязанных ClusterIP сервисов и конечных подов.


Итого при MetalLB External IP + Ingress запрос извне проходит следующую цепочку:
1. Приходит на внешний ip-адрес MetalLB L4-балансировщика (externalTrafficPolicy: Local type:LoadBalancer)
1. Из балансировщика перенаправляется в nginx-ingress-controller pod, с которым LB связан по лейблам
1. Из ingress-а запрос уходит на нужный ClusterIP сервис, который указан в rules и backend-е ingress.yaml
1. Из ClusterIP сервиса уже попадает в целевые pod-ы



В данном примере, все запросы, которые имеют header `x-region=us-east`, перенаправляются на поды canary, а те, которые не имеют, на предыдущие.
```
❯ curl -sk http://172.17.255.3/web/ | tail -n 3
172.17.0.2	web-794d999956-r56xs</pre>
</body>
</html>

❯ curl -sk -H "x-region: us-east" http://172.17.255.3/web/ | tail -n 3
172.17.0.11	web-canary-5585767dc6-8nncv</pre>
</body>
</html>
```

### Полезные варианты работы с Canary-аннотациями

Дальше, выбор ограничивается только параметрами запросов - крутой вариант использования, например по языкам или странам:

```
    nginx.ingress.kubernetes.io/canary-by-header: "Region"
    nginx.ingress.kubernetes.io/canary-by-header-pattern: "cd|sz"
```
Как предлагают тут - https://intl.cloud.tencent.com/document/product/457/38413.

Возможны и другие аннотации, помимо header-ов:
https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/annotations.md#canary

Более того самые полезные, имхо, `nginx.ingress.kubernetes.io/canary-weight: "10"`, так как они позволяют без изменения запросов просто бесшовно 10% траффика перенаправлять на выбранную группу подов.
https://mcs.mail.ru/help/ru_RU/cases-bestpractive/k8s-canary
https://v2-1.docs.kubesphere.io/docs/quick-start/ingress-canary/

## Flagger (Flux GitOps project)
Инструмент автоматизации развёртывания приложений в кубере  и его пример работы с canary и ингрессом:
https://docs.flagger.app/tutorials/nginx-progressive-delivery

```
Flagger implements several deployment strategies (Canary releases, A/B testing, Blue/Green mirroring) using a service mesh (App Mesh, Istio, Linkerd, Open Service Mesh) or an ingress controller (Contour, Gloo, NGINX, Skipper, Traefik) for traffic routing. For release analysis, Flagger can query Prometheus, Datadog, New Relic, CloudWatch or Graphite and for alerting it uses Slack, MS Teams, Discord and Rocket.
```

Прекрасное описание стретегий развёртывания
https://docs.flagger.app/usage/deployment-strategies

---

# Homework 5 (Volumes and Persistent storage)
## Synopsis

Тема огромна - проще прочитать документацию https://kubernetes.io/docs/concepts/storage/.

Чтобы напомнить про сущности, отмечу, что она содержит следующие пункты:
* Volumes
* Persistent Volumes
* Projected Volumes
* Ephemeral Volumes
* Storage Classes
* Dynamic Volume Provisioning
* Volume Snapshots
* Volume Snapshot Classes
* CSI Volume Cloning
* Storage Capacity
* Node-specific Volume Limits
* Volume Health Monitoring
* Windows Storage

Volume-ы (почти как в docker-е) нужны для 2х вещей:
1. Чтобы сохранять данные pod-а при рестарте контейнеров в нём. Так как по умолчанию перезапуск происходит начисто.
2. Чтобы контейнеры внутри pod-а могли совместно использовать файлы



## Volumes
**Volume** - абстракция реального хранилища (A directory containing data, accessible to the containers in a pod)
* Volume создается и удаляется вместе с подом (не экземпляром, а ресурсом)
* Один и тот же Volume может использоваться одновременно несколькими контейнерами в поде
Далее все volumes делятся на 2 вида - volume и persistent volume.

Что нужно запомнить про volume-ы (не эфемерные, не персистент и не конфигурационные)
1. При пересоздании контейнера сохраняются, но при пересоздании pod-а стираются, так как привязаны к нему. Можно сказать объект более низкого уровня вложенности. Типа Deployment > pod > volume
2. Сначала создаются volume-ы, потом уже поды, к которым они привязаны. Так что пока volume-а не будет, не будет pod-a
3. A pod can have multiple volumes and each container can mount zero or more of these volumes in different locations and can be of different types

* Persistent - отдельный объект, не связанный с жизненным циклом пода, поэтому устойчивый к любым пересозданиям нагрузок. Pod <--> Volume <--> External Storage
* Ephemeral - НЕ устойчивы к перезапуску контейнеров. Нужны для расширения лимитов, чаще используются для кеша.
* Projected - A projected (проецируемые) Одна директория volume mount-а содержит несколько вольюмов-источников разных типов конфигов (secret, downwardAPI, configMap, serviceAccountToken). Удобно для подов, требующих много конфигураций.
* Ephemeral - НЕ сохраняются при перезапуске контейнеров. Нужны для доп места, чаще под кеш. Может быть многих базовых типов: emptyDir, все volume-ы конфигов, CSI и тп.
* ConfigMap и Secret и другие конфиги - тоже вольюмы как правило.

Example of using a single volume in two containers are cases where a sidecar container runs a tool that processes or rotates the web server logs or when an init container creates configuration files for the main application container.

### Volume types
Non-exhaustive (Неисчерпывающий) list of the supported volume types:

* **emptyDir** — A simple directory that allows the pod to store data for the duration of its life cycle. The directory is created just before the pod starts and is initially empty - hence (следовательно) the name. The gitRepo volume, which is now deprecated, is similar, but is initialized by cloning a Git repository. Instead of using a gitRepo volume, it is recommended to use an emptyDir volume and initialize it using an init container.
* **hostPath** — Used for mounting files from the worker node’s filesystem into the pod.
* **nfs** — An NFS share mounted into the pod.
* **cloud disks**: gcePersistentDisk (Google Compute Engine Persistent Disk), awsElasticBlockStore (Amazon Web Services Elastic Block Store), azureFile (Microsoft Azure File Service), azureDisk (Microsoft Azure Data Disk) — Used for mounting cloud provider-specific storage.
* **Distributed storage**: cephfs, cinder, fc, flexVolume, flocker, glusterfs, iscsi, portworxVolume, quobyte, rbd, scaleIO, storageos, photonPersistentDisk, vsphereVolume — Used for mounting other types of network storage.
* **configMap**, **secret**, **downwardAPI**, and the **projected** volume type — Special types of volumes used to expose information about the pod and other Kubernetes objects
through files. They are typically used to configure the application running in the pod.
* **persistentVolumeClaim** — A portable way to integrate external storage into pods. Instead of pointing directly to an external storage volume, this volume type points to a PersistentVolumeClaim object that points to a PersistentVolume object that finally references the actual storage.
* **CSI** — A pluggable way of adding storage via the Container Storage Interface. This volume type allows anyone to implement their own storage driver that is then referenced in the csi volume definition. During pod setup, the CSI driver is called to attach the volume to the pod.


#### **emptyDir** (Common Volume type)
Просто пустая директория на хосте ноды, где запущен pod.

* Существует пока pod запущен
* Изначально создаётся пустой каталог на хосте (Директория типа /var/lib/kubelet/pods/<hash>/volumes)
* Все контейнеры в поде могут читать и записывать внутри файлы, причём монтирование может быть по разным путям
* Данные могут храниться в tmpfs (чревато OOM, зато очень быстро)

#### **hostPath** (Common Volume type)
Существующая директория на хосте ноды, где вызывается.

* Возможность монтировать файл или директорию с хоста
* Часто используется для служебных сервисов
    * Node Exporter
    * Fluentd/Fluent Bit
    * running cAdvisor in a container; use a hostPath of /sys
    * running a container that needs access to Docker internals; use a hostPath of /var/lib/docker
* Scheduler не учитывает hostPath в своих алгоритмах размещения pod-а на ноду
* Типов монтирования много:
    * DirectoryOrCreate
    * Directory
    * Socket
    * CharDevice
    * BlockDevice
    * FileOrCreate
    * File
* Кубер не рекомендует, так как очень небезопасно как с точки зрения привилегий, так и с точки зрения разницы сред
* На его основе делают множество csi, например persistent Volume provisioner - https://github.com/rancher/local-path-provisioner.

### subPath
Можно использовать один и тот же вольюм в двух контейнерах, но при этом разбивать его на поддиректории.
Например все данные приложения для бэкапа хранить в одном вольюме, но по разным маунтпоинтам и путям:
```

      image: mysql
      env:
      - name: MYSQL_ROOT_PASSWORD
        value: "rootpasswd"
      volumeMounts:
      - mountPath: /var/lib/mysql
        name: site-data
        subPath: mysql
    - name: php
      image: php:7.0-apache
      volumeMounts:
      - mountPath: /var/www/html
        name: site-data
        subPath: html
```
**Kubernetes supports two volumeModes of PersistentVolumes: Filesystem and Block.**
Их целое множество - cephfs volume, azureFile CSI migration, glusterfs, iscsi, etc.

#### Ephemeral Volumes

Очень узкоспециализированная штука.
Pod перезапускается - данные не сохраняются.

Полезно для кеширующих серверов и приложений, которые или для каких-нибудь данных только для чтения в виде файлов: ключей или конфигов.

Могут быть видов: emptyDir, configMap, downwardAPI, secret, generic ephemeral volumes и CSI ephemeral volumes с отслеживанием объёма.

Преимущества такого подхода:
* хранилище может быть локальным, либо подключаемым по сети;
* тома могут иметь заданный размер, который не может быть превышен приложением;
* работает с любыми драйверами CSI, поддерживающими предоставление постоянных томов и (для поддержки отслеживания емкости) реализующими вызов GetCapacity;
* тома могут иметь некоторые начальные данные, зависящие от драйвера и параметров;
* все типовые операции с томом (создание снимка состояния, изменение размера и т.п.) поддерживаются;
* тома можно использовать с любым контроллером приложений, принимающим спецификацию модуля или тома;
* планировщик Kubernetes сам выбирает подходящие узлы, поэтому больше не нужно обеспечивать и настраивать расширения планировщика и изменять webhooks.

Зачем так заморачиваться, а не хранить всё в контейнере, если всё равно сотрётся?
* Постоянная память в качестве замены оперативной памяти для memcached
* Локальное хранилище LVM в качестве рабочего пространства
* Можно создавать предзаполненный volume или CSI клон или копию

#### downwardAPI
Позволяет контейнерам внутри pod-ов получать информацию о самих себе и своих pod-ах.
##### Expose Pod Information to Containers Through Files
There are two ways to expose Pod and Container fields to a running Container:
* Environment variables
* Volume Files
Together, these two ways of exposing Pod and Container fields are called the Downward API.

Downward API volume:
```
  volumes:
    - name: podinfo
      downwardAPI:
        items:
          - path: "labels"
            fieldRef:
              fieldPath: metadata.labels
          - path: "annotations"
            fieldRef:
              fieldPath: metadata.annotations
          - path: "cpu_limit"
            resourceFieldRef:
              containerName: client-container
              resource: limits.cpu
              divisor: 1m
```
```
cat /etc/podinfo/labels

cluster="test-cluster1"
rack="rack-22"
zone="us-est-coast"
```


### Projected volume
A projected (запланированный или спроецированный?) volume maps several existing volume sources into the same directory.

In 1.26, the following types of volume sources can be projected:
* secret
* downwardAPI
* configMap
* serviceAccountToken

All sources are required to be in the same namespace as the Pod.
```
apiVersion: v1
kind: Pod
metadata:
  name: volume-test
spec:
  containers:
  - name: container-test
    image: busybox:1.28
    volumeMounts:
    - name: all-in-one
      mountPath: "/projected-volume"
      readOnly: true
  volumes:
  - name: all-in-one
    projected:
      sources:
      - secret:
          name: mysecret
          items:
            - key: username
              path: my-group/my-username
      - downwardAPI:
          items:
            - path: "labels"
              fieldRef:
                fieldPath: metadata.labels
            - path: "cpu_limit"
              resourceFieldRef:
                containerName: container-test
                resource: limits.cpu
      - configMap:
          name: myconfigmap
          items:
            - key: config
              path: my-group/my-config
```

### local (Static Persistent Local Volume)
PV являющийся примонтированным локальным хранилищем - директорией, разделом или диском.

Не поддерживает динамический провижининг.

Лучше, чем hostpath, так как не нужно явно указывать привзяку подов к ноде - scheduler сам знает как распределять поды и вольюмы, размещая связанные поды на нодах с local volume-ом.

То есть это более надёжное и гибкое решение, однако, ограниченное тем, что диск физически привязан к хосту ноды и поломка ноды означает поломку работы пода.

## Out-of-tree volume plugins
Всё это, конечно, не полный список, а с помощью  Container Storage Interface (CSI) и FlexVolume кто угодно может создавать плагины для хранилищ без необходимости менять код кубера.

## The StorageClass Resource
По факту yaml, похожий на CRD, который просто регистрирует ваше имя класса, связанный с ним плагин провижинера и поля класса, которые могут использовать pod-ы при вызове PVC с этим storage-классом.

Причём и ключи и допустимые значения этих полей мы задаём сами, естесственно.
Например: `class:nfs  drive_type:nvme`

### Provisioner
Имя storage plugin-а, который по факту будет выполнять операции с дисками, который привязан к storage class-у.

Есть список встроенных плагинов, но его можно расширять: https://kubernetes.io/docs/concepts/storage/storage-classes/#provisioner

### Allow Volume Expansion
PersistentVolumes can be configured to be expandable. This feature when set to true, allows the users to resize the volume by editing the corresponding PVC object. Volumes support volume expansion, when the underlying StorageClass has the field allowVolumeExpansion set to true.

## Container Storage Interface (CSI)

Defines a standard interface for container orchestration systems (like Kubernetes) to expose arbitrary storage systems to their container workloads.

Once a CSI compatible volume driver is deployed on a Kubernetes cluster, users may use the csi volume type to attach or mount the volumes exposed by the CSI driver.

A csi volume can be used in a Pod in three different ways:

* through a reference to a PersistentVolumeClaim
* with a generic ephemeral volume (alpha feature)
* with a CSI ephemeral volume if the driver supports that (beta feature)

## Persistent Volumes
* Создаются на уровне кластера
* PV похожи на обычные Volume, но имеют отдельный от сервисов жизненный цикл

Но их уже нельзя просто "объявить" - нужно реализовать привязку нагрузки к PV через PVC.

Отдельно, стоит выделить local volume - так как он привязывается к ноде. https://kubernetes.io/docs/concepts/storage/_print/#local

## PVC aka persistentVolumeClaim
Запрос на использование какого-либо PV для POD-а.
То есть это способ привязки без необходимости углубления в детали конкретной технологии фс и её реализации.

Администратор кластера может ограничить:
* Количество PVC в неймспейсе
* Размер хранилища, который может запросить PVC
* Объем хранилища, который может иметь неймспейс

### Claims As Volumes
Вообще PVC это отдельный объект и может объявляться в самостоятельных манифестах, однако возможно объявление прямо в pod.spec:
```
spec:
  containers:
    - name: myfrontend
      image: nginx
      volumeMounts:
      - mountPath: "/var/www/html"
        name: mypd
  volumes:
    - name: mypd
      persistentVolumeClaim:
        claimName: myclaim
```
### Expanding Persistent Volumes Claims
Поддержка авторасширения pvc доступна с 1.11 и включена по умолчанию, но работает далеко не со всеми storage class.

You can only expand a PVC if its storage class's allowVolumeExpansion field is set to true.
### CSI Volume expansion
То же доступно и для CSI - должно поддерживаться целевым драйвером.

You can only resize volumes containing a file system if the file system is XFS, Ext3, or Ext4.

### PVC & PV lifecycle
Provisioning > binding > using

Provisioning - статический (выдали все pv заранее и pvc привязывается к существующим) и динамический (реализуется через default storage class - происходит запрос pvc и кластер сам создаёт необходимый PV под его запрос, после чего происходит привязка)

Для следующих этапов есть разные инструменты защиты от переиспользования и перезаписи.

### PV Reclaiming
PV может иметь несколько разных политик переиспользования ресурсов хранилища:
* **Retain** - после удаления PVC, PV переходит в состояние “released”, чтобы переиспользовать ресурс, администратор должен вручную удалить PV, освободить место во внешнем хранилище (удалить данные или сделать их резервную копию)
* **Delete** - (плагин должен поддерживать эту политику) PV удаляется вместе с PVC и высвобождается ресурс во внешнем хранилище
* **Recycle** (deprecated в пользу dynamic provisioning-а) - удаляет все содержимое PV и делает его доступным для использования

### PV Access Modes
Тома монтируются к кластеру с помощью различных провайдеров, они имеют различные разрешения доступа чтения/записи, PV дает общие для всех провайдеров режимы.
PV монтируется на хост с одним их трех режимов доступа:
* **ReadWriteOnce** - **RWO** - только один узел может монтировать том для чтения и записи. ReadWriteOnce может предоставлять доступ нескольким подам, **если они запущены на одной node-е**.
* **ReadOnlyMany** - **ROX** - несколько узлов могут монтировать том для чтения
* **ReadWriteMany** - **RWX** - несколько узлов могут монтировать том для чтения и записи
* **ReadWriteOncePod** - **RWOP** - Только для единственного pod-а в рамках всего кластера. Поддержка только для CSI k8s 1.22+

### ConfigMap & Secret

Надо отметить, что эти два типа ресурсов так же в основном являются PV, но могут использоваться и в виде переменных.

#### **СonfigMap** - хранят:
* конфигурацию приложений
* значения переменных окружения отдельно от конфигурации пода
* Не шифруются, поэтому для любых приватных данных нужно использовать secret

#### **Secret** - хранят чувствительные данные (возможно шифрование содержимого в etcd, но в манифестах - base64)

You can store secrets in the Kubernetes API and mount them as files for use by pods without coupling to Kubernetes directly. secret volumes are backed by tmpfs (a RAM-backed filesystem) so they are never written to non-volatile storage.

#### ConfigMap & Secret типа функционируют следующим образом:
1. Сначала создаем соответствующий ресурс (ConfigMap, Secret)
2. В конфигурации пода в описании volumes или переменных окружения ссылаемся на созданный ресурс

## ConfigMaps
Нужны, очевидно, чтобы отделять данные от приложения, что полезно для безоапсности и переносимости.

A ConfigMap is an API object used to store non-confidential data in key-value pairs. Pods can consume ConfigMaps as **environment variables, command-line arguments, or as configuration files in a volume**. In addition thereis a crazy way to write code to run inside the Pod that uses the Kubernetes API to read a ConfigMap.

The name of a ConfigMap must be a valid DNS subdomain name.

Mounted ConfigMaps are updated automatically.
ConfigMaps consumed as environment variables are not updated automatically and require a pod restart.

**Caution**: ConfigMap does not provide secrecy or encryption. If the data you want to store are confidential, use a Secret rather than a ConfigMap, or use additional (third party) tools to keep your data private.

A ConfigMap is not designed to hold large chunks of data. The data stored in a ConfigMap cannot exceed 1 MiB. If you need to store settings that are larger than this limit, you may want to consider mounting a volume or use a separate database or file service.

Unlike most Kubernetes objects that have a spec, a ConfigMap has data and binaryData fields. The data field is designed to contain UTF-8 strings while the binaryData field is designed to contain binary data as base64-encoded strings.

Immutable Secrets and Immutable ConfigMaps - имеют смысл, когда конфигов очень много: защищены от записи и отключают автоматическое слежение за их обновлениями.

## Secret

A Secret is an object that contains a small amount of sensitive data such as a password, a token, or a key.

The name of a Secret object must be a valid DNS subdomain name.

Так же как и ConfigMap-ы:
1. Ограничены размером в мегабайт
2. Чаще volume-s, реже - переменные среды для пода.

Kubernetes Secrets are, by default, **stored unencrypted** in the API server's underlying data store (etcd)! In order to safely use Secrets, take at least the following steps - https://kubernetes.io/docs/concepts/security/secrets-good-practices/

Данные для секретов записываются в 2х форматах - `data` и `stringData`.
data - base64 encoded.

There are 3 main ways for a Pod to use a Secret:
* As files in a volume mounted on one or more of its containers.
* As container environment variable.
* By the kubelet when pulling images for the Pod.



| Builtin Type | Usage |
| --- | --- |
| Opaque (Generic)                      | arbitrary user-defined data |
| kubernetes.io/service-account-token   | service account token |
| kubernetes.io/dockercfg               | serialized ~/.dockercfg file |
| kubernetes.io/dockerconfigjson        | serialized ~/.docker/config.json file |
| kubernetes.io/basic-auth              | credentials for basic authentication |
| kubernetes.io/ssh-auth                | credentials for SSH authentication |
| kubernetes.io/tls                     | data for a TLS client or server |
| bootstrap.kubernetes.io/token         | bootstrap token data |

Secrets могут быть примонтированы как data volumes или как environment variables, чтобы использоваться контейнером в Pod.


## Непрозрачный тип данных - Opaque data type

Opaque - непрозрачный, матовый, мрак.

В информатике непрозрачный тип данных - это тип данных, чья конкретная структура данных не определена в интерфейсе. Это позволяет скрывать информацию, поскольку его значениями можно управлять только путем вызова подпрограмм, которые имеют доступ к недостающей информации. Конкретное представление типа скрыто от пользователей, а видимая реализация является неполной. Тип данных, представление которого является видимым, называется прозрачным. Непрозрачные типы данных часто используются для реализации абстрактных типов данных.

Типичные примеры непрозрачных типов данных включают дескрипторы для ресурсов, предоставляемых операционной системой к прикладному программному обеспечению. Например, стандарт POSIX для потоков определяет API на основе непрозрачных типов, которые представляют потоки или примитивы синхронизации как мьютексы или условные переменные.

Непрозрачный указатель - это особый случай непрозрачного типа данных.
Это указатель на структуру данных какого-то неопределенного типа.
Например, стандартная библиотека, которая является частью спецификации языка программирования C, предоставляет функции ввода-вывода для файлов, которые возвращают или принимают значения типа «указатель на FILE», представляющие собой файловые потоки, но конкретная реализация типа FILE является скрытой.

Также, если открыть Wireshark и посмотреть на содержание фрейма, с запросом к kubectl к api-server, в котором есть данные прикладного уровня, то можно увидеть подобную картину, где данные приложения зашифрованы и называются Opaque Type:
```
Frame 27: 577 bytes on wire (4616 bits), 577 bytes captured (4616 bits) on interface wlp2s0, id 0
Ethernet II, Src: #####, Dst: #####
Internet Protocol Version 4, Src: #####, Dst: #####
Transmission Control Protocol, Src Port: 37568, Dst Port: 443, Seq: 352, Ack: 1797, Len: 511
Transport Layer Security
    TLSv1.3 Record Layer: Application Data Protocol: http-over-tls
        Opaque Type: Application Data (23)
        Version: TLS 1.2 (0x0303)
        Length: 81
        Encrypted Application Data: e06d882842c816e3395035ef01a7aab11335d1260b450f11d52776695fe53a9029f36bf2…
        [Application Data Protocol: http-over-tls]
    TLSv1.3 Record Layer: Application Data Protocol: http-over-tls
        Opaque Type: Application Data (23)
        Version: TLS 1.2 (0x0303)
        Length: 420
        Encrypted Application Data: 1d9c6319480e2ddb80c336c82cb60edee0226b4b2872a24be0505e4588bb72ee28be73ac…
        [Application Data Protocol: http-over-tls]
```


### Opaque in Kubernetes Secrets

Получается, что в случае кубера идея была в том, что создав секрет, получающий из него данные pod, не может получить список всех ключей в нём, но может использовать из него значения, только если точно знает имя ключа.

### Immutable Secrets
    * protects you from accidental (or unwanted) updates that could cause applications outages
    * improves performance of your cluster by significantly reducing load on kube-apiserver, by closing watches for secrets marked as immutable.

### Projection of Secret keys to specific paths

Крутая опция, позволяющая выбирать из всех ключей сикрета только определённые и маппить их по разным путям.

You can also control the paths within the volume where Secret keys are projected. You can use the .spec.volumes[].secret.items field to change the target path of each key:
```
apiVersion: v1
kind: Pod
metadata:
  name: mypod
spec:
  containers:
  - name: mypod
    image: redis
    volumeMounts:
    - name: foo
      mountPath: "/etc/foo"
      readOnly: true
  volumes:
  - name: foo
    secret:
      secretName: mysecret
      items:
      - key: username
        path: my-group/my-username
```
What will happen:
1. the username key from mysecret is available to the container at the path /etc/foo/my-group/my-username instead of at /etc/foo/username.
1. the password key from that Secret object is not projected.

### Risks
  * In the API server, secret data is stored in etcd; therefore:
    * Administrators should enable encryption at rest for cluster data (requires v1.13 or later).
    * Administrators should limit access to etcd to admin users.
    * Administrators may want to wipe/shred disks used by etcd when no longer in use.
    * If running etcd in a cluster, administrators should make sure to use SSL/TLS for etcd peer-to-peer communication.
  * If you configure the secret through a manifest (JSON or YAML) file which has the secret data encoded as base64, sharing this file or checking it in to a source repository means the secret is compromised. Base64 encoding is not an encryption method and is considered the same as plain text.
  * Applications still need to protect the value of secret after reading it from the volume, such as not accidentally logging it or transmitting it to an untrusted party.
  * A user who can create a Pod that uses a secret can also see the value of that secret. Even if the API server policy does not allow that user to read the Secret, the user could run a Pod which exposes the secret.


В общем base64 - это прокатит, если хочется скрыть от беглого взгляда, но лучше шифровать.

#### Container image pull secrets (private image repo access)
If you want to fetch container images from a private repository, you need a way for the kubelet on each node to authenticate to that repository. You can configure image pull secrets to make this possible. These secrets are configured at the Pod level.

## PVC earning lifecycle
Стандартный путь:
1. Создаётся StorageClass, который позволяет привязать реальное хранилище к pv
2. Создаётся PV
3. Создаётся PVC пользователем
4. Кубер находит подходящий под PVC PV
5. Создаётся POD с volume-ом, который ссылается на PVC

Кстати надо будет руками потом подчищать ненужные PV - это место на всякий случай навсегда занимается.
### В какой момент происходит монтирование
1. Kubernetes монтирует сетевой диск на ноду
2. Runtime пробрасывает том в контейнер

## The StorageClass Resource
Описание "классов" различных систем хранения
Разные классы могут использоваться для:
* Произвольных политик (например переиспользования?)
* Динамического provisioning

У каждого StorageClass есть provisioner, который определяет какой плагин используется для работы с PVs.

### Provisioner
Для того, чтобы storage class мог физически управлять выданным ему хранилищем существует Provisioner - т.е. код, который непосредственно отправляет ему вызовы.

## Dynamic Volume Provisioning
Dynamic volume provisioning allows storage volumes to be created on-demand.
The implementation of dynamic volume provisioning is based on the API object StorageClass from the API group storage.k8s.io.
A cluster administrator can define as many StorageClass objects as needed, each specifying a volume plugin (aka provisioner) that provisions a volume and the set of parameters to pass to that provisioner when provisioning.

Важно, что после удаления statefulset-а PVC и PV остались в кластере, пока не удалил PVC руками. Тогда уже и связанный PV удалился, так как был с reclaim политикой Delete:



#### Resizing a volume containing a file system
You can only resize volumes containing a file system if the file system is XFS, Ext3, or Ext4 in RWX.

## StatefulSet
PODы в StatefulSet отличаются от других нагрузок:
* Каждый под имеет уникальное состояние (имя, сетевой адрес и volume-ы)
* Так как поды в StatefulSet имеют разное состояние для обеспечения сетевой связности должен использоваться Headless Service
* Volume-ы для подов должны создаваться через PersistentVolume
* Для каждого pod-а создается отдельный PVC
* Удаление/масштабирование подов не удаляет тома, связанные с ними
* Масштабирование выполняется последовательно: следующий под будет создан только вслед за предыдущим
* У каждого pod свой pvc и свой pv, поэтому надо пользоваться секцией volume claim template
* Если pod оказался на авайриной ноде - поведение будет отличаться от поведения в deployment
* Уникальные, предсказуемые имена pod (app-1, app-2)

Часто сравнивают подходы с репликам и сейтфулсетам как к стаду и к питомцам - в первом случае важно количество и идентичность, во втором - уникальность и качество.

## Local Path Provisioner (local dynamic provisioner)
Local Path Provisioner provides a way for the Kubernetes users to utilize the local storage in each node. Based on the user configuration, the Local Path Provisioner will create either hostPath or local based persistent volume on the node automatically. It utilizes the features introduced by Kubernetes Local Persistent Volume feature, but makes it a simpler solution than the built-in local volume feature in Kubernetes.

### Immutable Secrets
    * protects you from accidental (or unwanted) updates that could cause applications outages
    * improves performance of your cluster by significantly reducing load on kube-apiserver, by closing watches for secrets marked as immutable.

### Risks
  * In the API server, secret data is stored in etcd; therefore:
    * Administrators should enable encryption at rest for cluster data (requires v1.13 or later).
    * Administrators should limit access to etcd to admin users.
    * Administrators may want to wipe/shred disks used by etcd when no longer in use.
    * If running etcd in a cluster, administrators should make sure to use SSL/TLS for etcd peer-to-peer communication.
  * If you configure the secret through a manifest (JSON or YAML) file which has the secret data encoded as base64, sharing this file or checking it in to a source repository means the secret is compromised. Base64 encoding is not an encryption method and is considered the same as plain text.
  * Applications still need to protect the value of secret after reading it from the volume, such as not accidentally logging it or transmitting it to an untrusted party.
  * A user who can create a Pod that uses a secret can also see the value of that secret. Even if the API server policy does not allow that user to read the Secret, the user could run a Pod which exposes the secret.


В общем base64 - это норм, если хочется скрыть от беглого взгляда, но в идеале, лучше шифровать.


### Kubernetes some CSI list

https://github.com/kubernetes-csi/docs/blob/master/book/src/drivers.md

На самом деле важны:
1. Dynamic provisioning
1. Лёгкость в обслуживании (реплики, бэкапы, восстановления и тп)
1. kube-native установка - operator, helm, yaml
1. POSIX FS (ну когда как)
1. Snapshots
1. И другие фишки типа Thin provisioning и т.п.

* https://github.com/longhorn/longhorn - божественно удобный тул, который ставится одним йамлом в т.ч. и даже в установки типа k3s, но требует на ноде драйвера sudo apt-get install -y open-iscsi
Поддерживает ReadWriteMany, thin-provisioned и тп.
When the Longhorn Manager is asked to create a volume, it creates a Longhorn Engine instance on the node the volume is attached to, and it creates a replica on each node where a replica will be placed. The Longhorn Engine always runs in the same node as the Pod that uses the Longhorn volume. It synchronously replicates the volume across the multiple replicas stored on multiple nodes.
* https://github.com/rook/rook - очень страшно тк ceph =), только если установка-поддержка простые, не тюнить глубоко
* https://github.com/kubernetes-sigs/nfs-ganesha-server-and-external-provisioner - It works just like in-tree dynamic provisioners: a StorageClass object can specify an instance of nfs-ganesha-server-and-external-provisioner to be its provisioner. Then, the instance of nfs-ganesha-server-and-external-provisioner will watch for PersistentVolumeClaims that ask for the StorageClass and automatically create NFS-backed PersistentVolumes for them.
* https://github.com/seaweedfs/seaweedfs - CSI, мелкий, но перспективный
* https://github.com/kadalu/kadalu: A lightweight Persistent storage solution for Kubernetes / OpenShift / Nomad using GlusterFS in background.
* https://github.com/juicedata/juicefs - требует первоначальной настройки внешнего кластера
* https://github.com/cubeFS/cubefs - замороченно, слишком много ручной работы
* https://docs.ondat.io/docs/install/kubernetes/ (storageos) - CSI, dynamic, operator требует лицензию даже для бесплатной версии =( b2b
* https://github.com/quobyte/quobyte-k8s-resources - CSI, operator, dynamic b2b
* https://github.com/NetApp/beegfs-csi-driver - Ставить тяжко, Dynamic, выглядит как b2b для ML
## Homework part

### MinIO StatefulSet
Интересно, что у pvc есть поле status, но остальные статусы отображаются аннотациями
```
Annotations:   pv.kubernetes.io/bind-completed: yes
               pv.kubernetes.io/bound-by-controller: yes
               volume.beta.kubernetes.io/storage-provisioner: rancher.io/local-path
               volume.kubernetes.io/selected-node: kind-control-plane
               volume.kubernetes.io/storage-provisioner: rancher.io/local-path
Finalizers:    [kubernetes.io/pvc-protection]
```

Важный момент, что **сначала создаётся PVC, а затем создаётся PV под него в случае динамического провижининга**. При этом сначала даже образ контейнеров пода не пуллится - будет ждать пока либо админ либо провижинер не создадут PV для привязки.

```
❯ k get ev
LAST SEEN   TYPE     REASON                  OBJECT                               MESSAGE
5m21s       Normal   WaitForFirstConsumer    persistentvolumeclaim/data-minio-0   waiting for first consumer to be created before binding
5m21s       Normal   ExternalProvisioning    persistentvolumeclaim/data-minio-0   waiting for a volume to be created, either by external provisioner "rancher.io/local-path" or manually created by system administrator
5m21s       Normal   Provisioning            persistentvolumeclaim/data-minio-0   External provisioner is provisioning volume for claim "default/data-minio-0"
5m19s       Normal   ProvisioningSucceeded   persistentvolumeclaim/data-minio-0   Successfully provisioned volume pvc-f3a65b28-a1ba-4b83-a109-22326015c61f
5m18s       Normal   Scheduled               pod/minio-0                          Successfully assigned default/minio-0 to kind-control-plane
5m17s       Normal   Pulling                 pod/minio-0                          Pulling image "minio/minio:RELEASE.2019-07-10T00-34-56Z"
3m26s       Normal   Pulled                  pod/minio-0                          Successfully pulled image "minio/minio:RELEASE.2019-07-10T00-34-56Z" in 1m51.278097132s
3m26s       Normal   Created                 pod/minio-0                          Created container minio
3m26s       Normal   Started                 pod/minio-0                          Started container minio
5m21s       Normal   SuccessfulCreate        statefulset/minio                    create Claim data-minio-0 Pod minio-0 in StatefulSet minio success
5m21s       Normal   SuccessfulCreate        statefulset/minio                    create Pod minio-0 in StatefulSet minio successful
```
В ДЗ предлагают использовать для просмотра mc, но есть ui, в котором можно работать с бакетами по 9000 порту. Забавно, что он показывает использованное пространство для всего сегмента фс, а не для pvc в 10 гигабайт, который ему по идее должен быть выдан.


То есть порядок действий следующий:
* Создаётся statefulset с MinIO, у которого есть просто volume, в котором он будет хранить данные
* Вместе с ним создаётся RWO volumeClaim, который запрашивает у дефолтного storage class квоту на pv со storageClass=standard и volumeMode=filesystem, т.е. дефолтные значения
* А всё потому что в kind-е по умолчанию установлен rancher/local-path-provisioner в одноимённом ns.
То есть он выдаёт на каждый PVC PV, выделяя целиком (тк лимиты пока игнорирует) `hostPath` диск динамически - очень удобная штука в случае использованя bare-metal и отсутствия network storage.

При этом, если удалить statefulSet, то и pv и pvc останутся, пока pvc не будет удалён вручную.

Примечательно, что директория, в которой находятся загруженные в бакет файлы, находится буквально за 2 команды:
```
❯ k describe pv | grep Path
    Type:          HostPath (bare host directory volume)
    Path:          /var/local-path-provisioner/pvc-51dd3f17-f33b-4ac4-a959-9d77e6d7368d_default_data-minio-0
    HostPathType:  DirectoryOrCreate
```
и переходя в контейнер kind-а и поддиректорию бакета, который создал из ui:
```
root@kind-control-plane:~# ls -lhF /var/local-path-provisioner/pvc-51dd3f17-f33b-4ac4-a959-9d77e6d7368d_default_data-minio-0/bucket/
total 16M
-rw-r--r-- 1 root root 16M Dec 15 17:35 Kubernetes_in_Action_Second_Edition_v14.pdf
```
### Secret creation
В нашем случае секретами являются MINIO_ACCESS_KEY и MINIO_SECRET_KEY, которые подтягиваются в приложение как переменные среды, поэтому проще всего поступить так:
1. **Так как секреты хранятся в base64, используем** `echo -n <var_name> | base64`
1. Создаём секрет типа opaque, в который кладём эти закодированные переменные
1. В поде меняем значение на переменную из ключа секрета:
```
env:
  - name: MINIO_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: minio-secret
        key: MINIO_ACCESS_KEY
```


---
# Homework 6 (Security and AAAA)
## The 4C's of Cloud Native Security
Cloud > Cluster > Container > Code

Each layer of the Cloud Native security model builds upon the next outermost layer. The Code layer benefits from strong base (Cloud, Cluster, Container) security layers. You cannot safeguard against poor security standards in the base layers by addressing security at the Code level.

В данной методологии описаны общие подходы ко всей безопасности инфраструктуры.
В принципе, её следует брать как гайдлайн и по шагам защищать свою инфраструктуру.
https://kubernetes.io/docs/concepts/security/overview/

## The 4A's. Security classic AAA + A (4A) in K8s:
* Authentication (to identify)
* Authorization (to give permission)
* Auditing (aka accounting - to log an audit trail)
* Admission controllers (content of action validation)

На этом и строится основное управление безопасностью
https://kubernetes.io/docs/concepts/security/controlling-access/

Все управления доступом появились из-за multitenancy.
Поэтому кубер решил CNI, CSI и CRI сделать заменяемыми, но управления безопасностью спроектировать и сделать самостоятельно, так как лучше знает как в деталях и меньше косяков будет у пользователей.

## Authentication

В Kubernetes API нет как таковых привычных сущностей аккаунтов с паролями или их групп для аутентификации.

Есть следующие сущности:

**Users**
* Это люди, которые отдают команды кластеру
* Глобальны в рамках кластера
* Не управляются из API

**Service Accounts**
* Привязаны к жизни ресурса или процесса в кластере
* Локальны в Namespace
* Управляются из API
* Привязаны к токену из Secrets, позволяют элементам кластера общаться с API

Всё, что можно делать через serviceAccount нужно делать через него, так как он namespaced, управляется через кластер, срок действия и легче ограничить только нужным функционалом.

Есть такие варианты аутентификации, но в основном используются выделенные:
* **X509 Client Certs**
* **Static Token File /Static Password File**
* **OpenID Connect Tokens**
* Bootstrap Tokens /Service Account Tokens
* Webhook Token Authentication
* Authenticating Proxy
* Анонимный запрос

## Authorization
### Namespaces
Области видимости в кластере - грубо, виртуальные "подкластеры".

Часть api-resources являются namespaced (e.g. Deployment, Service), то есть ограниченнми областью видимости, часть - нет (e.g. PV, ClusterRole)

### Default Service Account
`Default Service Account` - Создаётся автоматически вместе с namespace-ом, он присваивается новым подам, чтобы они могли обращаться в Kube API.
Когда создаёшь SA, то для него кубер автоматически создаёт secret, а именно - токен!


## Webhook
На события аудита в кластере можно повесить вебхук, который будет предпринимать какие-то действия связанные с безопасностью.

## ABAC

В подавляющем большинстве случаев используется RBAC, а не ABAC.

Attribute-based access control (ABAC) defines an access control paradigm whereby access rights are granted to users through the use of policies which combine attributes together.

To enable ABAC mode, specify --authorization-policy-file=SOME_FILENAME and --authorization-mode=ABAC on startup.

The file format is one JSON object per line. There should be no enclosing list or map, only one map per line.

Each line is a "policy object", where each such object is a map.

Bob can just read pods in namespace "projectCaribou":
`{"apiVersion": "abac.authorization.kubernetes.io/v1beta1", "kind": "Policy", "spec": {"user": "bob", "namespace": "projectCaribou", "resource": "pods", "readonly": true}}`


### RBAC
Чтобы использовать RBAC (хороший акроним ККК - кого, как и кто или who whom how (wwhh?)) нужно:
1. Иметь роль, которая позволяет проводить операции (глаголы) над ресурсами (объектами). **Role/ClusterRole**.
1. Иметь Субъект (т.е. совершающего действия). Subjects (**users**, **groups**, or **service accounts**)
1. Связать Роль с Субъектом. **RoleBinding/ClusterRoleBinding** через roleRef.

#### Role and ClusterRole
`Роль = операция + ресурс`.
E.g.: Читать эндпоинты, создавать PV и тп.

Когда речь идёт об операциях с ресурсами, стоит вспомнить:
**CRUDL** - новшество в букве L: create read update delete **list**

Основное - это apiGroups и группы ресурсов, к которым мы даем доступ:

```
rules:
- apiGroups: [""] # "" означает apiGroup под именем core или legacy
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

В Kubernetes имеются следующие роли по умолчанию:

* view: доступ только для чтения, исключает секреты;
* edit: перечисленное выше + возможность редактировать большинство ресурсов, исключает роли и привязки ролей;
* admin: перечисленное выше + возможность управлять ролями и привязками ролей на уровне пространств имен;
* cluster-admin: все возможные привилегии.


#### RoleBinding ClusterRoleBinding
* RoleBinding - привязка внутри одного namespace
* ClusterRoleBinding - на весь кластер

В Binding секция roleRef отвечает за привязку.

Если привязать кластерную роль через обычный RoleBinding, то она будет действовать только в рамках неймспейса RoleBinding!

Важно, что в кубере множество механизмов защиты требуют неизменяемости ресурсов.
Например roleRef - если роль привязал, то всё, роль изменять нельзя, так как очевидно небезопасно:
```
After you create a binding, you cannot change the Role or ClusterRole that it refers to. If you try to change a binding's roleRef, you get a validation error. If you do want to change the roleRef for a binding, you need to remove the binding object and create a replacement.
```
Т.е. как только у binding-а появились субъекты - нельязя менять роли, которые в связке roleRef перечислены.
Это связано с тем, что
1. Неизменность roleRef позволяет управлять только списком субъектов (исполнителей), но не менять права, которые им назначены ролью и binding-ом.
1. Привязка к другой роли (т.е. другим правам для всей общности субъектов) - это фундаментально другой уровень асбракции. Требование пересоздания binding-а, для изменения связи между субъетом и ролью, гарантирует, что всем субъектам нужна новая роль, а не что права лишним субъектам выдадут случайно.

#### Удобный механизм создания шаблонов ролей
A RoleBinding can also reference a ClusterRole to grant the permissions defined in that ClusterRole to resources inside the RoleBinding's namespace. This kind of reference lets you define a set of common roles across your cluster, then reuse them within multiple namespaces.

### Пересоздание roleref
С помощью `kubectl auth reconcile` можно создавать манифесты, которые позволяют пересоздавать привязки, если требуется.

Вопрос - а что тогда с ролью? Её можно менять и это ок, что все субъекты получат другие права на ресурсы?
Звучит вроде нормально, примерно так, если бы в линуксе группе lol выдали бы права на новую директорию.

Интересно, что есть ClusterRole, но это совсем не значит, что права будут на весь кластер - можно сделать привязку такой роли в пределах одного namespace.
https://kubernetes.io/docs/reference/access-authn-authz/rbac/#user-facing-roles

При этом, чтобы дать возможность всем service account-ам одного namespace-а права на доступ ко всему кластеру нужно использовать cluser role binding, но с ограничением `kind: Group name: system:serviceaccounts:namespace`.

Роли можно объединять в общности посредством aggregated clusterroles с помощью лейблов: https://kubernetes.io/docs/reference/access-authn-authz/rbac/#aggregated-clusterroles

### rakkess
Невероятно удобный плагин для krew, строящий матрицу для пользователей и сервисных аккаунтов

`kubectl access-matrix -n my-project-dev --as jean`

https://github.com/corneliusweig/rakkess

## Admission controllers
Node, ABAC, RBAC и webhook отвечают только за авторизацию операций по отношению к ресурсам, но не за само содержание этих операций.

Поэтому, в довесок к тем 4м способам авторизации, сделали admission controller (контроллер входа, признания, допуска) - грубо говоря контроллер контента.

То есть одно дело пользователь получил доступ к домашней странице на портале, другое - он в поля пытается вписать SQL-инъекцию.

AC может делать две важные функции:
* Изменять запросы к API (JSON Patch)
* Пропускать или отклонять запросы к API
Каждый контроллер может делать обе вещи, если захочет.
❗ Но сначала отрабатывают мутаторы, изменяющие запросы, а потом - валидаторы на них.

Например, есть такие:
**NamespaceLifecycle**:
* Запрещает создавать новые объекты в удаляемых Namespaces
* Не допускает указания несуществующих Namespaces
* Не дает удалить системные Namespaces

**ResourceQuota** (ns) ограничивает:
- кол-во объектов
- общий объем ресурсов
- объем дискового пространства для volumes

**LimitRanger** (ns) Возможность принудительно установить ограничения по ресурсам pod-а.

**NodeRestriction** - Ограничивает возможности kubelet по редактированию Node и Pod

**ServiceAccount** - Автоматически подсовывает в Pod необходимые секреты для функционирования Service Accounts

**Mutating + Validating AdmissionWebhook** - Позволяют внешним обработчикам вмешиваться в обработку запросов, идущих через AC

**Node auth** - Авторизация на ноде - полезно например для команды наблюдения, которая собирает часть метрик нужной какой-нибудь группы - аналитики, безопасность. Или например ноды со специальными настройками для БД.


## Отличная статья по сертификатам, RBAC и администрированию прав
Cтатья посвящена тому, как создавать пользователей, используя клиентские сертификаты X.509, и как управлять авторизацией с помощью базовых API-объектов RBAC в Kubernetes. Мы также поговорим о некоторых открытых проектах, упрощающих администрирование кластера: rakkess, kubectl-who-can, rbac-lookup и RBAC Manager.

https://habr.com/ru/company/flant/blog/470503/

### Статья, описывающая реальные пути применения RBAC и IAM в кластере
https://thenewstack.io/three-realistic-approaches-to-kubernetes-rbac/
### Утилиты, позволяющие агрегировать и отобразить матрицы прав в кластере
https://www.freshbrewed.science/k8s-and-krew-rbac-utilities/index.html

## Pod Security Admission controller (Replacer for PodSecurityPolicy)

Kubernetes offers a built-in Pod Security admission controller to enforce the Pod Security Standards. Pod security restrictions are applied at the namespace level when pods are created.

Задаёте полики ограничений для всех подов в неймспейсах и, если они их нарушают, то в зависимости от режима, происходит какое-то событие безопасности - либо отмену действия, либо запись в общий лог, либо просто предупреждение пользователя.

Для более гибкого управления, можно делать исключения для определённых пользователей, неймспейсов или рантайм классов.

Pod Security Standards используются, чтобы определить уровни изоляции pod-ов.

Pod Security Standards определяют три разных политики, что широко закрывают потребности безопасности.

Политики суммируются и варьируются от всеразрешающих до всезапрещающих.

Pod Security admission places requirements on a Pod's Security Context and other related fields in yaml according to the three levels defined by the Pod Security Standards: privileged, baseline, and restricted

Pod Security Admission labels for namespaces
1. **Privileged** -	Unrestricted policy, providing the widest possible level of permissions. This policy allows for known privilege escalations.
1. **Baseline** -	Minimally restrictive policy which prevents known privilege escalations. Allows the default (minimally specified) Pod configuration.
1. **Restricted** -	Heavily restricted policy, following current Pod hardening best practices.

#### Примеры некоторых объектов контроля и режимы исполнения политик:
* HostProcess
* HostPath Volumes
* AppArmor
* Seccomp
* Capabilities
* Host Ports
* /proc Mount Type
* https://kubernetes.io/docs/concepts/security/pod-security-standards/

(!) И эта одна из причин почему кубер только на линуксе (не юниксе), так как только в нём есть все эти плюшки с сигруппами, неймспейсами, селинуксами и тп.

**Modes for namespaces:**
* **enforce**	Policy violations will cause the pod to be rejected.
* **audit**	Policy violations will trigger the addition of an audit annotation to the event recorded in the audit log, but are otherwise allowed.
* **warn**	Policy violations will trigger a user-facing warning, but are otherwise allowed.

#### Exemptions
Allows the creation of pods that would have otherwise been prohibited due to the policy associated with a given namespace. Configured in the Admission Controller configuration.

* **Usernames**: requests from users with an exempt authenticated (or impersonated) username are ignored.
* **RuntimeClassNames**: pods and workload resources specifying an exempt runtime class name are ignored.
* **Namespaces**: pods and workload resources in an exempt namespace are ignored.

### Alternative 3rd party policy agents

#### Kyverno open policy agent

Kyverno — решение для автоматизации (policy engine), управления и обеспечения безопасности любой платформы на базе Kubernetes.
Kyverno работает как динамический контроллер допуска в кластере.
Он получает от kube-apiserver HTTP-обратные вызовы вебхуков с проверкой и изменением допусков и применяет соответствующие политики для получения результатов, которые обеспечивают соблюдение политик допуска или отклоняют запросы.

Политики Kyverno написаны на родном для Kubernetes языке YAML, что значительно сокращает время обучения, необходимое для написания собственных политик.
Политики Kyverno могут сопоставлять ресурсы, используя селекторы типа ресурса, имени и метки, чтобы инициировать такие действия, как проверка, изменение, генерация и верификация образа для подписи контейнеров и сертификации цепочки программного обеспечения.

#### Kubewarden
Kubewarden is a policy engine for Kubernetes. It helps with keeping your Kubernetes clusters secure closed_lock_with_key and compliant heavy_check_mark

Kubewarden policies can be written using regular programming languages or Domain Specific Languages (DSL).

Policies are compiled into WebAssembly modules that are then distributed using traditional container registries.

https://github.com/kubewarden

#### Gatekeeper open policy agent
Gatekeeper — специфическая реализация Open Policy Agent (OPA) для Kubernetes, которая работает в качестве Webhook для валидации манифестов. Этот инструмент предназначен для аудита и автоматического применения к ресурсам Kubernetes политик безопасности, написанных на языке Rego.

Gatekeeper встраивается между сервером API Kubernetes и OPA, принимает все поступающие в кластер запросы и в реальном времени проверяет их на соответствие предварительно настроенным политикам безопасности. 

https://habr.com/ru/company/vk/blog/669788/


## Auditing

Kubernetes auditing provides a security-relevant, chronological set of records documenting the sequence of actions in a cluster. The cluster audits the activities generated by users, by applications that use the Kubernetes API, and by the control plane itself.
Audit records begin their lifecycle inside the kube-apiserver component. Each request on each stage of its execution generates an audit event, which is then pre-processed according to a certain policy and written to a backend. The policy determines what's recorded and the backends persist the records. The current backend implementations include logs files and webhooks.

https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/


### Оффтоп
Есть 2 балансировщика:
* Application Layer Balancer (L7)
* Network Layer Balancer (L4)

Зачем L7 нужен, казалось бы, когда есть более низкоуровневые и более быстрые L4?
Затем, что данные зашифрованы, а NLB, могут читать только заголовки пакетов, но не данные внутри.
Вспомнился forward proxy TLS termination с Varnish.

## Homework part

Есть множество предустановленных ролей в кластере, которые можно посмотреть `k get clusterroles`, а потом `describe`. Например для SA PV-провижинера в kind:
```
❯ k describe clusterrole local-path-provisioner-role
Name:         local-path-provisioner-role
Labels:       <none>
Annotations:  <none>
PolicyRule:
  Resources                      Non-Resource URLs  Resource Names  Verbs
  ---------                      -----------------  --------------  -----
  endpoints                      []                 []              [*]
  persistentvolumes              []                 []              [*]
  pods                           []                 []              [*]
  events                         []                 []              [create patch]
  configmaps                     []                 []              [get list watch]
  nodes                          []                 []              [get list watch]
  persistentvolumeclaims         []                 []              [get list watch]
  storageclasses.storage.k8s.io  []                 []              [get list watch]
```

Судя по тому, что `Permissions are purely additive (there are no "deny" rules).` - если мы хотим запретить доступ к кластеру, то нужно просто создать пользователя, не давая привязок.

Удостоверился - всё что у него есть такой командой `kubectl access-matrix --as dave`:
```
selfsubjectaccessreviews.authorization.k8s.io                       ✔
selfsubjectrulesreviews.authorization.k8s.io                        ✔
```

Важно не забывать, что основная игра в гибкости и шаблонизации основана на том, что RoleBinding к ClusterRole всё равно привязан к неймспейсу.

И что у пользователей в subject `apiGroup: rbac.authorization.k8s.io`, а у SA - `namespace` =)



---
# Homework 7 (Helm and templating)

## Helm
Возможности
* Упаковка нескольких манифестов Kubernetes в пакет - Chart
* Установка пакета в Kubernetes (установленный Chart называется Release)
* Изменение значений переменных во время установки пакета
* Upgrade (обновления) и Rollback (откаты) установленных пакетов
* Управление зависимостями между пакетами
* Xранение пакетов в удаленных репозиториях

Фактически очень гибкий щаблонизатор с широченными возможностями - куча встроенных переменных, возможность получения переменных и шаблонов отовсюду, тесты и тп. Есть опции  `--dry-run --debug`, которые позволяют проверить шаблоны на правильное вычисление значений и тп.

```
example/
  Chart.yaml         # описание пакета
  README.md
  requirements.yaml  # список зависимостей
  values.yaml        # переменные
  charts/            # загруженные зависимости
  templates/         # шаблоны описания ресурсов Kubernetes
```

Документация сама является прекрасным пошаговым руководством - https://helm.sh/docs/chart_template_guide/getting_started/

Если подумать, то чарты, однозначно полезнее в случае, когда необходимо заниматься дистрибуцией своего приложения, в то время как управление через GitOps, типа ArgoCD или Flux, гораздо удобнее, когда в этом нет необходимости.

### Встрооенные переменные

* Release - информация об устанавливаемом release
* Chart - информация о chart, из которого происходит установка
* Files - возможность загружать в шаблон данные из файлов (например, в configMap )
* Capabilities - информация о возможностях кластера (например, версия Kubernetes)
* Templates - информация о манифесте, из которого был создан ресурс

Внутри этих классов могут быть весьма сложные и полезные вроде:
* `Files.AsSecrets` is a function that returns the file bodies as Base 64 encoded strings.
* `Capabilities.APIVersions.Has $version` indicates whether a version (e.g., batch/v1) or resource (e.g., apps/v1/Deployment) is available on the cluster.

### Циклы, условия и функции
В основе Helm лежит шаблонизатор Go с 50+ встроенными функциями.

Например:

**Условия**:
```
{{- if .Values.server.persistentVolume.enabled }}
    persistentVolumeClaim:
      ...
{{- else }}
```

**Циклы**:
```
{{- range $key, $value := .Values.server.annotations }}
  {{ $key: }} {{ $value }}
{{- end }}
```

**Операторы сравнения**:
`eq, ne, lt, gt, and, or ...`

**Printf**:
```
name: {{ printf "%s-master" (include "common.names.fullname" .) }}
---
common.names.fullname: redis
---
name: redis-master

```
Список большой - https://helm.sh/docs/chart_template_guide/function_list/

### Pipelines

По аналогии с пайпами в unix

One of the powerful features of the template language is its concept of pipelines. Drawing on a concept from UNIX, pipelines are a tool for chaining together a series of template commands to compactly express a series of transformations. In other words, pipelines are an efficient way of getting several things done in sequence.

`drink: {{ .Values.favorite.drink | repeat 5 | quote }}`

приведёт к повторению переменной 5 раз и последующему заключению в кавычки

`drink: "coffeecoffeecoffeecoffeecoffee"`

Ещё есть фунции default и lookup:
* drink: {{ .Values.favorite.drink | default "tea" | quote }}
* The `lookup` function can be used to look up resources in a running cluster.  When lookup returns a list of objects, it is possible to access the object list via the items field:
```
{{ range $index, $service := (lookup "v1" "Service" "mynamespace" "").items }}
    {{/* do something with each service */}}
{{ end }}
```
For templates, the operators (eq, ne, lt, gt, and, or and so on) are all implemented as functions. In pipelines, operations can be grouped with parentheses ((, and )).


### Hooks
Определенные действия, выполняемые в различные моменты жизненного цикла поставки. Hook, как правило, запускает Job (но это не обязательно).

Виды hooks:
* `pre/post-install`
* `pre/post-delete`
* `pre/post-upgrade`
* `pre/post-rollback`

### Использование публичных чартов, но своих переменных
`helm install chartmuseum chartmuseum/chartmuseum -f kubernetes-templating/chartmuseum/values.yaml --namespace=chartmuseum --create-namespace`

### Поиск по центральному хабу и своим репозиториям
* `helm search hub` searches the Artifact Hub (like docker hub), which lists helm charts from dozens of different repositories. (e.g. https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack)
* `helm search repo` searches the repositories that you have added to your local helm client (with `helm repo add`). This search is done over local data, and no public network connection is needed.

### Helm Secrets
Плагин helm-secrets (https://github.com/jkroepke/helm-secrets) предлагает секретное управление и защиту вашей важной информации. Он делегирует секретное шифрование Mozilla SOPS.
Ставится самим хелмом в сам хелм и, используя разные механизмы шифрования, может на лету расшифровывать зашифрованные значения в применяемых манифестах или шаблонах.

Важно, что команда в таком случае заменяется с `helm upgrade` на `helm secrets upgrade`.

Шифрование может осуществляться, например находящимися на машине PGP-ключами (например парой RSA), с которой выполняются `helm secrets upgrade` - то есть значения можно пушить в гит, но должна быть доверенная среда исполнения.

* Плагин для Helm
* Механизм удобного* хранения и деплоя секретов для тех, у кого нет HashiCorp Vault
* Реализован поверх другого решения - Mozilla Sops (https://github.com/mozilla/sops)
* Возможность сохранить структуру зашифрованного файла (YAML, JSON, ENV, INI and BINARY)
* Поддержка PGP и KMS (AWS KMS, GCP KMS, Azure Key Vault, age, and PGP.)

Очень полезная штука, когда нет Vault.

### Best practices
* В большинстве имён и переменных стоит привязываться не к названию пакета, а к версии релиза
* Указывайте все используемые в шаблонах переменные в values.yaml, выбирайте адекватные значения по умолчанию
* Используйте команду helm create для генерации структуры своего chart
* Пользуйтесь плагином helm docs для документирования своего chart

https://helm.sh/docs/chart_best_practices/

#### Chart, release and some valuable remarks
**Chart** - пакет, включающий
* Метаданные
* Шаблоны описания ресурсов Kubernetes
* Конфигурация установки (values.yaml)
* Документация
* Список зависимостей

**Release**
* Установленный в Kubernetes Chart
* Хранятся в configMaps и Secrets
* Chart + Values = Release
* 1 Upgrade = 1 Release

A chart can be either an 'application' or a 'library' chart.
* Application charts are a collection of templates that can be packaged into versioned archives to be deployed.
* Library charts provide useful utilities or functions for the chart developer. They're included as a dependency of application charts to inject those utilities and functions into the rendering pipeline. Library charts do not define any templates and therefore cannot be deployed.

Для того, чтобы переопределить values для subchart-а необходимо в основном файле values прописать секцию с именем зависимости и в ней переопределить значения.

У чарта могут быть тесты - например connection test после установки.
Информация, которая выводится в аутпут после установки чарта формируется через NOTES.txt - например, ссылка на внешнее доменное имя, токены доступа и дальнейшие инструкции по конфигурации.

**“.”** означает текущую область значений (current scope), далее идет зарезервированное слово Values и путь до ключа. При рендере релиза сюда подставится значение, которое было определено по этому пути.

### 3-way merge
Работает Helm 3 следующим образом:

1. **1** Получает на вход Chart (локально или из репозитория, при этом чарты могут использовать друг друга) и генерирует манифест релиза.
1. **2** Получает текст предыдущего релиза.
1. **3** Получает текущее стостояние примитивов из namespace-релиза.
1. Сравнивает эти три вещи, делает patch и передает его в KubeAPI.
1. Дожидается выката релиза (опциональный шаг).

Эта схема называется 3-way merge. Таким образом Helm приведет конфигурацию приложения к состоянию, которое описано в git, но не тронет другие изменения. Т. е., если у вас в кластере есть какая-то сущность, которая трансформирует ваши примитивы (например, Service Mesh), то Helm отнесется к ним бережно.

### Subcharts
* A subchart is considered "stand-alone", which means a subchart can never explicitly depend on its parent chart.
* For that reason, a subchart cannot access the values of its parent.
* A parent chart can override values for subcharts.
* Helm has a concept of global values that can be accessed by all charts.

helm upgrade --install hipster-shop kubernetes-templating/hipster-shop --namespace hipster-shop **--set frontend.service.NodePort=31234**
Так как как мы меняем значение переменной для зависимости - перед названием
переменной указываем имя (название chart) этой зависимости.

##### Следующая аннотация позволяет развертывать новые Deployments при изменении ConfigMap:
```
kind: Deployment
spec:
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

##### Отказ от удаления ресурсов с помощью политик ресурсов (PVC for example):
```
metadata:
  annotations:
    "helm.sh/resource-policy": keep
```

## "Sealed Secrets" for Kubernetes by bitnami
https://github.com/bitnami-labs/sealed-secrets

Encrypt your Secret into a SealedSecret, which is safe to store - even to a public repository. The SealedSecret can be decrypted only by the controller running in the target cluster and nobody else (not even the original author) is able to obtain the original Secret from the SealedSecret.

## Helmfile

* Надстройка над helm - шаблонизатор шаблонизатора.
* Управление развертыванием нескольких Helm Charts на нескольких окружениях
* Возможность устанавливать Helm Charts в необходимом порядке
* Больше шаблонизации, в том числе и в values.yaml
* Поддержка различных плагинов (helm-tiller, helm-secret, helm-diﬀ)
* Главное - не увлечься шаблонизацией и сохранять прозрачность решения
```
releases:
- name: prometheus-operator
  chart: stable/prometheus-operator
  version: 6.11.0
  <<: *template
- name: prometheus-telegram-bot
  chart: express42/prometheus-telegram-bot
  version: 0.0.1
  <<: *template
...
    - ./values/{{`{{ .Release.Name }}`}}.yaml.gotmpl
```
Отличная статья по использованию helmfile как IaC с разделением окружений https://habr.com/ru/post/491108/ и Ссылка на репо с правильной иерархией директорий - https://github.com/zam-zam/helmfile-examples.

### Божественная фича - возможность накатывать простые yaml манифесты из поддиректорий!

Создаёшь поддиректорию в которой находится нечто, что создаётся вне чартов.
Например, ClusterIssuer для cert-manager-а и helmfile автоматически его поставит.
```
- name: cert-manager-cluster-issuer
  chart: ./issuer-cr
```
### Если важна последовательная установка чартов из манифестов
`helmfile sync --concurrency=1 ...`

## Jsonnet

* Продукт от Google
* Расширение JSON (как YAML - нужно помнить, что любой json представим в виде yaml)
* Любой валидный JSON - валидный Jsonnet (как YAML)
* Полноценный язык программирования* (заточенный под шаблонизацию) (не как YAML)

### Зачем (в подовляющем большинстве случаев - незачем)

* Для генерации и применения манифестов множества однотипных ресурсов, отличающихся несколькими параметрами
* Если есть ненависть к YAML, многострочным портянкам на YAML и отступам в YAML
* Для генерации YAML и передачи его в другие утилиты (например - kubectl):
* `kubecfg show workers.jsonnet | kubectl apply -f -`

### Kubecfg
Самый лучший на данный момент тул для работы с Jsonnet-ом.

Позволяет делать шаблоны манифестов в виде json-шаблонов используя библиотеку для интерпретации, например - libsonnet.

Общий workﬂow следующий:
1. Импортируем подготовленную библиотеку с описанием ресурсов https://github.com/bitnami-labs/kube-libsonnet/blob/v1.19.0/kube.libsonnet
1. Пишем общий для сервисов шаблон
1. Наследуемся от шаблона, указывая конкретные параметры

## Kustomize

* Поддержка встроена в kubectl
* Кастомизация готовых манифестов
* Все больше приложений начинают использовать kustomize как альтернативный вариант поставки (istio, nginx-ingress, etc...)
* Почти как Jsonnet, только YAML (но kustomize - это не templating)
* Нет параметризации при вызове, но можно делать так: `kustomize edit set image ...`

### Общая логика работы:
1. Создаем базовые манифесты ресурсов
1. Создаем файл kustomization.yaml с описанием общих значений
1. Кастомизируем манифесты и применяем их (Можно делать как на лету, так и по очереди)
1. Отлично подходит для labels , environment variables и много чего еще

## cert-manager
Интересный инструмент, позволяющий автоматизировать работу с сертификатами.
Причём провайдерами могут выступать как Let’s Encrypt, HashiCorp Vault и Venafi, так и private PKI.

Туториал для LetsEncrypt + Ingress-Nginx https://cert-manager.io/docs/tutorials/acme/nginx-ingress/.

Другие полезные руководства, включая работу с gcloud, GKE и DNS; Istio; а также локальные варианты - https://cert-manager.io/docs/tutorials/.

Для отладки используется великолепное приложение kuard от создателей книги Kubernetes Up and running, которое позволяет получить исчёрпывающую инфу о кластере и работе сети - https://github.com/kubernetes-up-and-running/kuard.

Тип CRD Issuer определяет как cert-manager будет запрашивать TLS-сертификаты. Важно, что Issuers принадлежат namespace-ам, но есть также ClusterIssuer, который можно установить для всего кластера.
Подробнее обо всех CRD - https://cert-manager.io/docs/concepts/.

Для того, чтобы с помощью let's encrypt-а можно было получить сертификат, нужно выполнить следующее:

1. Иметь в кластере ingress-контроллер (простейший пример - nginx)
2. Установить в кластер сам cert-manager и его CRD (ставятся обычно отдельно, но можно и через чарт `--set installCRDs=true`)
3. Иметь публичное (доступное для LE) доменное имя или зону, которая будет подтверждать сертификат
4. Создать ingress для целевого сервиса, в котором будут аннотации на эмитента сертификата и блок с секретом tls:

```
  annotations:
    kubernetes.io/ingress.class: "nginx"
    #cert-manager.io/issuer: "letsencrypt-staging"
spec:
  tls:
  - hosts:
    - example.example.com
    secretName: quickstart-example-tls
```
5. Дальше работа идёт с 2мя видами эмитентов LE - staging и prod, потому что можно легко выйти за лимиты попыток подтверждения сертификатов у LE и нужно сначала протестировать корректность всей связки.

Создаётся
```
   apiVersion: cert-manager.io/v1
   kind: Issuer
   metadata:
     name: letsencrypt-prod
```
через который на ингресс и делается фактический запрос у LE.

Важно, что ingress annotation для ClusterIssuer пишется через дефис: `cert-manager.io/cluster-issuer`

6. Deploy a TLS Ingress Resource

Если выполнены все требования, то можно делать запрос на TLS сертификат.
Для этого существуют 2 способа:
1. Аннотации в ingress через ingress-shim (который отслеживает все ингрессы в кластере и запрашивает подходящим сертификаты)
2. Прямое создание ресурса сертификата

Проще первый путь, так как простое раскомментирование строки `#cert-manager.io/issuer: "letsencrypt-staging"` позволяет cert-manager
* Создать автоматом сертификат
* Создаст или изменит ingress чтобы использовать его для подтверждения домена (что обычно в html/.well-known/token.html)
* Подтвердить домен
* После того как домен подтверждён и выдан, cert-manager создаст и/или обновит секрет в сертификате

Проверяем состояние выдачи `kubectl describe certificate quickstart-example-tls` и сам секрет серта `kubectl describe secret quickstart-example-tls`

#### Cert-manager Debug
Удобно дебажить делая describe следующим ресурсам, если что-то пошло не так.

```
❯ k -n harbor describe certificaterequests.cert-manager.io
Events:
  Type    Reason           Age    From                                                Message
  ----    ------           ----   ----                                                -------
  Normal  cert-manager.io  2m36s  cert-manager-certificaterequests-approver           Certificate request has been approved by cert-manager.io
  Normal  IssuerNotFound   2m36s  cert-manager-certificaterequests-issuer-vault       Referenced "Issuer" not found: issuer.cert-manager.io "letsencrypt-prod" not found
```
После фикса
```
❯ k -n harbor get certificates.cert-manager.io
NAME             READY   SECRET           AGE
harbor-ingress   True    harbor-ingress   71s
```

## Homework part

Чтобы для GKE из локального терминала получать креды через `gcloud`, необходимо установить auth-plugin:
`gcloud components install gke-gcloud-auth-plugin` и `export USE_GKE_GCLOUD_AUTH_PLUGIN=True` (https://cloud.google.com/blog/products/containers-kubernetes/kubectl-auth-changes-in-gke).

После уже можно использовать новую команду без **beta** вида: `gcloud container clusters get-credentials <cluster_name>`


Stable helm переехал : https://helm.sh/blog/new-location-stable-incubator-charts/,
в связи с чем нужна команда `helm repo add stable https://charts.helm.sh/stable`

| Name | Old Location | New Location |
|------|--------------|--------------|
|stable|https://kubernetes-charts.storage.googleapis.com | https://charts.helm.sh/stable |

#### **--atomic**
Самый полезный ключ это `--atomic`: if set, the installation process deletes the installation on failure. The **--wait** flag will be set **automatically** if --atomic is used.
Он меня спас несколько раз, подчищая за неудавшимися установками хвосты, которые могли бы приводить к конфликтам или мисконфигурациям.

##### Nginx-ingress helm installation

В итоге использовал самую последнюю версию ингресса,
`helm upgrade --install nginx-ingress ingress-nginx/ingress-nginx --atomic --namespace=nginx-ingress --version=4.4.0`,
репо, которой взял отсюда: https://kubernetes.github.io/ingress-nginx/deploy/#quick-start.


##### Cert-manager helm and CRD installation
https://github.com/cert-manager/cert-manager/blob/master/deploy/charts/cert-manager/README.template.md

Before installing the chart, you must first install the cert-manager CustomResourceDefinition resources. This is performed in a separate step to allow you to easily uninstall and reinstall cert-manager without deleting your installed custom resources.

CRD содержат сертификаты, CA, заказы сертификатов, типы проверок и тп.
Именно поэтому, чтобы не относится к релизам и случайно не стирать сертификаты и историю их установка не включа в хелм чарт по умолчаню (To automatically install and manage the CRDs as part of your Helm release, you must add the `--set installCRDs=true` flag to your Helm installation command).

`kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/{{RELEASE_VERSION}}/cert-manager.crds.yaml`

После установки CRD можно устанавливать релиз из чарта.

`helm install cert-manager-{{RELEASE_VERSION}} --namespace cert-manager --version {{RELEASE_VERSION}} jetstack/cert-manager --atomic`

##### A-record IP <---> Domain
Далее пришлось A-запись, указывающую на адрес в своём DNS-е.

##### Настройка LE как issuer-а
Automated Certificate Management Environment (ACME) https://cert-manager.io/docs/configuration/acme/ бывают 3х видов, но используются 2:
1. HTTP01 - создаёт ключ, доступный по http url-у, который будет соответствовать запрашиваемому доменному имени.
2. DNS01 - нужно добавить ключ в TXT-запись, после чего сервер ACME, сделав lookup,  challenges are completed by providing a computed key that is present at a DNS TXT record.

Так как у LE жёсткие лимиты на количество запросов подтверждения, то необходимо создать 2 CRD Issuer-а - один для тестов, а другой для боевого применения.

Адреса для HTTP01-проверки у Let's Encrypt так и разделяются:
1. https://acme-staging-v02.api.letsencrypt.org/directory
2. https://acme-v02.api.letsencrypt.org/directory

```
spec:
  acme:
    # The ACME server URL
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    # Email address used for ACME registration
    email: some@gmail.com
    # Name of a secret used to store the ACME account private key
    privateKeySecretRef:
      name: letsencrypt-staging
    # Enable the HTTP-01 challenge provider
    solvers:
    - http01:
        ingress:
          class:  nginx
```

После того как Issuer-ы будут созданы, cert-manager будет знать как и куда обращаться за сертификатом и подтверждением того, что доменное имя действительно принадлежит ресурсу.

##### Развёртка Ingress с TLS
Теперь, наконец, можно запрашивать сертификаты.

Когда у нас есть серт-менеджер, который знает как и куда обращаться, статический айпишник, по которому доступен ингресс-контроллер извне, доменное имя для ингресса с записью для этого айпишника.

Для этого можно использовать 2 способа:
1. Используя аннотации в ingress через ingress-shim (контоллер cert-manager, следящий за ингрессами, чтобы вязать к ним сертификаты https://cert-manager.io/docs/usage/ingress/)
2. Напрямую создавать кастом ресурс типа Certificate

Далее мы используем автоматизированный вариант с аннотациями, чтобы ingress-shim создал ресурс сертификата. После его создания cert-manager  обновит или создаст ingress для подтверждения домена. Как только домен будет подтверждён cert-manager создаст secret, который определён в ресурсе certificate.
То есть ресурс сертификата ссылается на секрет! А внутри самого секрета уже пэйлод сертификата.
Важно, что имена и ссылки в ингрессах, сертификатах и секретах должны совпадать.

После редактирования cert-manager.io/issuer
```
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/issuer: "letsencrypt-staging"
```
Получаем: `(STAGING) Let's Encrypt` - то есть полный порядок, получили тестовый сертификат от LE, можно запрашивать настоящий через `cert-manager.io/issuer: "letsencrypt-prod"`

```
❯ k get certificates.cert-manager.io
NAME                     READY   SECRET                   AGE
quickstart-example-tls   True    quickstart-example-tls   8m23s
```
и в браузере `Verified by: Let's Encrypt`


### Chartmuseum
Чарт устарел и не разрабатывается: его нельзя поставить на кластер 1.22 и выше (https://kubernetes.io/docs/reference/using-api/deprecation-guide/#ingress-v122), не отредактировав исходники, так как он использует неправильные пути к ресурсу ингресса в шаблонах:
```
❯ helm upgrade --install chartmuseum stable/chartmuseum --atomic \
--namespace=chartmuseum \
--version=2.14.2 \
-f chartmuseum/values.yaml
Release "chartmuseum" does not exist. Installing it now.
WARNING: This chart is deprecated
Error: unable to build kubernetes objects from release manifest: unable to recognize "": no matches for kind "Ingress" in version "networking.k8s.io/v1beta1"
```

Для этого приходится откатывать кластер!

### Chartmuseum | Задание со ⭐
#### Values auth
Для того, чтобы включить загрузку с помощью логина и пароля:
```
env:
  open:
  DISABLE_API: false
  secret:
    # username for basic http authentication
    BASIC_AUTH_USER:user
    # password for basic http authentication
    BASIC_AUTH_PASS:password
```

Docs - https://chartmuseum.com/docs/#uploading-a-chart-package

#### Создание чарта
Осуществляется командой Helm:
```
cd mychart/
helm package .
```
Также можно загрузить уже готовый чарт для prometheus-оператора напрямую по URL:
```
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm pull prometheus-community/kube-prometheus-stack -d ./
```
После этого появится файл `kube-prometheus-stack-43.1.1.tgz`

#### Загрузка в chartmuseum

Осуществляется командой:
`curl -u user:password --data-binary "@kube-prometheus-stack-43.1.1.tgz" https://chartmuseum.35.198.148.234.nip.io/api/charts`

Если же пакет подписан и для него существует provenance file, нужно его загрузить рядом:
`curl -u user:password --data-binary "@kube-prometheus-stack-43.1.1.tgz.prov" https://chartmuseum.35.198.148.234.nip.io/api/prov`

Можно загрузить одновременно оба файла используя /api/charts и multipart/form-data тип:
`curl -u user:password -F "chart=@kube-prometheus-stack-43.1.1.tgz" -F "prov=@kube-prometheus-stack-43.1.1.tgz.prov" https://chartmuseum.35.198.148.234.nip.io/api/charts`

Но можно использовать просто helm-push:

`helm push mychart/ chartmuseum`

#### Установка чарта в k8s:
Add the URL to your ChartMuseum installation to the local repository list:

```
helm repo add chartmuseum-nip https://chartmuseum.35.198.148.234.nip.io --username=user --password=password
"chartmuseum-nip" has been added to your repositories
```
После этого выполняется поиск по чартам музея:

`helm search repo chartmuseum-nip`

Выбирается нужный и устанавливается:
`helm install chartmuseum-nip/kube-prometheus-stack`

### Harbor Helm
Использую новую версию чарта, так как на текущих версиях GKE (kuber 1.24) возникают проблемы с совместимостью:
https://github.com/goharbor/harbor-helm/tree/v1.10.2

* expose.ingress.hosts.core - меняем на свой адрес
* expose.ingress.hosts.notary - глушим
* expose.ingress.className: `"nginx"`
* expose.ingress.annotations: `cert-manager.io/issuer: "letsencrypt-staging"`
* persistence.resourcePolicy: "" instead of keep for pvc auto
* `notary:   enabled: falseremoval`

Важно не забыть установить CR Issuer cert-manager-а в namespace harbor, так как они namespaced, а кластерные до этого не устанавливались!

```
helm upgrade --install harbor harbor/harbor --create-namespace \
--atomic \
--namespace=harbor \
--version=1.10.2 \
-f harbor/values.yaml
```
Конечно же я получил следующее:
```
Events:
  Type     Reason           Age   From                                          Message
  ----     ------           ----  ----                                          -------
  Warning  OrderFailed      12m   cert-manager-certificaterequests-issuer-acme  Failed to wait for order resource "harbor-ingress-zbgnq-3472572959" to become ready: order is in "errored" state: Failed to create Order: 429 urn:ietf:params:acme:error:rateLimited: Error creating new order :: too many certificates already issued for "nip.io". Retry after 2022-12-20T14:00:00Z: see https://letsencrypt.org/docs/rate-limits/
```
Поменял на своё доменное имя, предварительно связав IP ингресса с ним, после чего обновил чарт той же командой, что и устанавливал.
```
❯ kubectl get secrets -n harbor -l owner=helm
NAME                           TYPE                 DATA   AGE
sh.helm.release.v1.harbor.v1   helm.sh/release.v1   1      17m
sh.helm.release.v1.harbor.v2   helm.sh/release.v1   1      2m47s
```
Интересно, что при этом релиз приложения не изменился, но харбор сделал новый релиз, проставив свою версию.
После этого где-то вылез по таймауту при апгрейде и из-за atomic-а сделал автоматический roll-back.
Проблема оказалась почему-то в PVC и таймауте привязок, переустановка решила проблему.

### Helmﬁle | Задание со ⭐
Использую новую версию - https://github.com/helmfile/helmfile/blob/v0.149.0/docs/index.md

Переменные для harbor-а брал отсюда - https://github.com/goharbor/harbor-helm/tree/v1.10.2#configuration

Почему не вшили в cert-manager возможность ставить через helm nginx clusterIssuer-ов опционально, передавая доменное имя и email - неясно.

Решил следующим образом: в helmfile есть возможность накатывать обычные yaml манифесты, если их положить в поддиректорию. Главное, ставить последовательно  `--concurrency 1`, чтобы не было ошибки.


```
- name: cert-manager-cluster-issuer
  chart: ./issuer-cr
```
Интересно, что в качестве источника хелм чарта можно использовать даже гит с указанием ветки

`docker run --rm --net=host -v "${HOME}/.kube:/root/.kube" -v "${HOME}/.config/helm:/root/.config/helm" -v "${PWD}:/wd" --workdir /wd quay.io/roboll/helmfile:helm3-v0.142.0 helmfile sync`


Перед установкой, после сборки helmfile, делаю `helmfile lint`, чтобы убедится в доступности всех чартов.

Установка:
`helmfile sync -f helmfile.yaml --concurrency 1`

После всего стоит проверить, что адрес, который получил ингресс контроллер совпадает с указанным в DNS-записи.
`k get -n ingress-nginx svc ingress-nginx-controller  -o jsonpath="{.status.loadBalancer.ingress..ip}"`

## Создаем свой helm chart
Опять ошибка в домашке с out-of-date образами: указанный `image: gcr.io/google-samples/microservices-demo/adservice:v0.1.3` отсутствует в реджистри

https://console.cloud.google.com/gcr/images/google-samples/global/microservices-demo/adservice

Его нужно заменить на `v0.3.4` - тогда всё будет работать.


Несмотря на то, что все объекты предыдущих шагов были удалены, всё равно не хватило ресурсов в кластере - пришлось создавать ещё одну воркер ноду.

> Попробуйте обновить chart и убедиться, что ничего не изменилось

После замены `image: gcr.io/google-samples/microservices-demo/frontend:v0.1.3` на `image: gcr.io/google-samples/microservices-demo/frontend:{{ .Values.image.tag }}`,

и применения `helm upgrade -n hipster-shop frontend frontend/`, ничего не изменилось с точки зрения работы приложения, однако helm всё же пересоздаёт деплоймент. Это важно так как в некоторых случаях это может привести к нежелательным простоям или сбоям.



### Создаем свой helm chart | Задание со ⭐
requirements.yaml - устарел (https://helm.sh/blog/helm-3-preview-pt5/), и так как используется Helm v3, то стоит просто прописать redis как зависимость публичным чартом.

Я использовал чарт из хаба от Bitnami - https://artifacthub.io/packages/helm/bitnami/redis

В values.yaml
```
redis:
  auth.enabled: false
```
```
redis:
  nameOverride: redis-cart
  fullnameOverride: redis-cart
  architecture: standalone
  auth:
    enabled: false
```
И, так как для изменения имя сервиса, пришлось бы переписывать его (`name: {{ printf "%s-master" (include "common.names.fullname" .) }}`), в all-hipster-shop.yaml
```
image: gcr.io/google-samples/microservices-demo/cartservice:v0.1.3
env:
- name: REDIS_ADDR
  value: "redis-cart-master:6379"
```

### helm-secrets | Необязательное задание
Переместил секреты в kubernetes-templating/helm-secrets/move-to-frontend-chart, так как без моего ключа установка этого чарта будет вызывать ошибку.

`sudo curl -L -o /usr/local/bin/sops https://github.com/mozilla/sops/releases/download/v3.7.3/sops-v3.7.3.linux.amd64 && chmod +x /usr/local/bin/sops`

`helm plugin install https://github.com/jkroepke/helm-secrets --version v4.2.2`

`gpg --full-generate-key`

Где ID - строчка из шеснадцетиричного числа заглавными буквами.

`sops --encrypt --in-place --pgp <ID> secrets.yaml`

`helm secrets decrypt secrets.yaml` - если нужно посмотреть


### Предложите способ использования плагина helm-secrets в CI/CD
Простейшим способом кажется добавление gpg-ключа в secret variables или аналогичные системы.
Также можно записать ключ в образ, который будет производить работу с helm в CI.

Чтобы защититься от коммитов секретов в репо можно
1. В гитигнор добавить расширения RSA и тп
2. Ключи для подписи и тп класть только в переменные среды - остальное подписывать
3. Использовать сложные гит хуки или повесить проверку https://github.com/awslabs/git-secrets

## JSONnet Kubecfg (язык шаблонов для json)
Kubecfg архивирован и переехал:
https://github.com/vmware-archive/kubecfg#warning-kubecfg-is-no-longer-actively-maintained-by-vmware

Так как используемая в домашнем задании библиотека устарела и для деплоймента имела версию kube api apps/v1beta2, пришлось её обновить до коммита
https://github.com/bitnami-labs/kube-libsonnet/raw/96b30825c33b7286894c095be19b7b90687b1ede/kube.libsonnet

Итого иморт должен быть: `local kube = import "https://github.com/bitnami-labs/kube-libsonnet/raw/96b30825c33b7286894c095be19b7b90687b1ede/kube.libsonnet"`



## В манифестах нужно быть предельно внимательным к регистру и к автозаменам.
Ошибся как всегда на этой игре с именами полей и именами сущностей:

    `{{ if eq .Values.service.type "NodePort" }}nodePort: {{ .Values.service.NodePort }}{{ end }}`
1. NodePort - spec.type
1. nodePort - spec.ports
1. .Values.service.NodePort - ну а это переменная с произвольным именем из values

ПРИЧЁМ! Никакого сообщения не было, так как я ошибся в условии if: `type eq nodePort`, а обнаружил я это случайно, вызвав `get svc` и увидев, что порт не тот, что прописан в values.yaml.
Коварная штука в общем.



## Retrieving data from secrets

В секрете хранится иерархическая структура, легко представима в виде json или в виде yaml.

Поэтому к полям можно получить доступ через встроенный аналог jq в например так:
`kubectl get secrets/db-user-pass --template={{.data.password}} | base64 --decode` == `kubectl get secret db-user-pass -o jsonpath='{.data.password}' | base64 --decode`

Но так как содержимое секретных полей закодировано в base64, то необходима раскодировка на лету.

Если не хочется мучаться с двойными скобками и именами содержащими точку, то можно выводить в json и обрабатывать реальным jq:
`k -n harbor get secret letsencrypt-prod -o json | jq -r '.data."tls.key"' | base64 -d`



## GKE ingress static IP binding

Используются 2 аннотации в описании ингресса - класс и имя статического айпи, которое указывали при его создании.

```
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    # This tells Google Cloud to create an External Load Balancer to realize this Ingress
    kubernetes.io/ingress.class: gce
    # This enables HTTP connections from Internet clients
    kubernetes.io/ingress.allow-http: "true"
    # This tells Google Cloud to associate the External Load Balancer with the static IP which we created earlier
    kubernetes.io/ingress.global-static-ip-name: web-ip # This is the name of static IP in list
```

### Promote ephemeral to static IP

To promote the allocated IP to static, you can update the Service manifest:

`kubectl patch svc ingress-nginx-lb -p '{"spec": {"loadBalancerIP": "104.154.109.191"}}'`

... and promote the IP to static (promotion works differently for cloudproviders, provided example is for GKE/GCE):

`gcloud compute addresses create ingress-nginx-lb --addresses 104.154.109.191 --region us-central1`

---

## Yaml dot and nested element
Не стоит забывать, что такая запись:
```
redis:
  auth.enabled: false
```
Не равнозначна такой:
```
redis:
  auth:
    enabled: false
```
И, в случае, хелма, например, не не сработает и не вызовет ошибки!

---

# What is cgroup v2?
FEATURE STATE: Kubernetes v1.25 [stable]

cgroup v2 is the next version of the Linux cgroup API. cgroup v2 provides a unified control system with enhanced resource management capabilities.

cgroup v2 offers several improvements over cgroup v1, such as the following:

* Single unified hierarchy design in API
* Safer sub-tree delegation to containers
* Newer features like Pressure Stall Information (точнее отслеживает информацию о перегрузе железа и позволяет использовать ресурсы почти на 100%, отсекая ненужное и перераспределяя нагрузку)
* Enhanced resource allocation management and isolation across multiple resources
    * Unified accounting for different types of memory allocations (network memory, kernel memory, etc)
    * Accounting for non-immediate resource changes such as page cache write backs

Some Kubernetes features exclusively use cgroup v2 for enhanced resource management and isolation. For example, the MemoryQoS feature improves memory QoS (Quality-of-Service for Memory Resources) and relies on cgroup v2 primitives.

То есть только в v2 cgroup используются и limit и request-ы на память, так как в v1 использовались только limit-ы по факту. И в v1 не было механизма сжатия памяти, в случае, если оно подбиралась к лимиту, что приводило к OOM-ам. (https://kubernetes.io/blog/2021/11/26/qos-memory-resources/)


## Config best practice
Интересный хинт написан тут - https://kubernetes.io/docs/concepts/configuration/overview/#services.

Сказано, что первым лучше создавать сервисы для любого типа workload-а, так как в таком случае при инициализации они сразу подхватят нужные переменные и не будет задержек и race-ов.

Полагаю, что то же самое касается и сикретов с конфиг мапами - они при бутстраппинге будут прокинуты и приложение запустится быстрее и без проблем.

Так что общее правило - сначала всё подготовить для основного объекта, а только потом задеплоить его.

Вообще полезная страница, по ней можно делать финальную сверку своих конфигураций.


# Глоссарий Kubernetes-а
https://kubernetes.io/docs/reference/glossary/?all=true
# Если нужно найти инструмент для решения какой-то проблемы
То, в первую очередь нужно поискать его в ландшафте https://landscape.cncf.io/.

Там есть всё, начиная с CNI/CRI/CSI и Service Mesh, заканчивая SAST-ами и Chaos Engineering-ом.




