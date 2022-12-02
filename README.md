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
  * NoNewPrivileges , sysctl, AppArmor/SELinux профили
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
Cоздает имя,которое можно запросить при помощи DNS

Виды сервисов
* ClusterIP (+ Headless service `clusterIP: None`)
* NodePort
* LoadBalancer

## Local link
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
Этот вид сервиса предназначен только для облачных провайдеров
Которые своими программными средствами реализуют балансировку
нагрузки
В Bare Metal это делается чуть иначе - понадобится MetalLB

## Ingress
Объект управляющий внешним доступом к сервисам внутри кластера по факту набор правил внутри кластера Kubernetes.
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

Client <--https--> Proxy <--http--> Application

Механизм, при котором запросы снаружи до reverse-proxy идут как обычно шифрованные, но уже от reverse-proxy до приложения идут без шифрования трафика.

Это позволяет разгрузить сервер приложения и оставить эту работу reverse-proxy севрверу.
Также, если прокся дешифрует трафик, то она начинает понимать его содержимое, а значит, может баланисровать, кешировать и тп

Offloads main server crytpo
TLS closer to client
HTTP accelerators (Varnish)
Intrusion detection systems - если тебя атакуют проще сниффить трафик после дешифровки
Load balancing/Service mesh


В случае kubernetes это легко можно осуществлять с помощью ingress.

## TLS Forward Proxy
Но так же есть ещё и фокус сделать TLS forward proxy.

Суть в том, что происходит то же TLS termination, только трафик уже шифруется между Proxy и бэкендом своим собственным ключом после его дешифровки проксёй.

Это, с одной стороны позволяет дешифровывать трафик и управлять им - балансировать и кешировать, с другой, устраняет незащищённый канал между бэком и проксёй.

Client <----https enc1----> Proxy <----https enc2----> Application

hostNetwork: true
Если я указываю для Pod это свойство, то сетевой Namespace не
создается
Pod напрямую видит сетевые адаптеры ноды
Так работают Pod, которые реализуют сетевую подсистему, например
Никто не мешает сделать так Ingress Pod c ingress-nginx


hostPort для контейнера
Я могу указать для контейнера порт, который будет открыт на ноде
На ноде,где в итоге оказался Pod
Так не могут делать несколько контейнеров по понятной причине
Опять же,для Ingress Pod почему бы и нет

externalIP для Service
Я могу указать конкретные внешние сетевые адреса для сервиса
Тогда в iptables будут созданы необходимые пробросы внутрь
Мы уже их видели


## Homework part

1. Почему следующая конфигурация валидна, но не имеет смысла?
livenessProbe:
exec:
command:
- 'sh'
- '-c'
- 'ps aux | grep my_web_server_process'

PID 1

2. Бывают ли ситуации, когда она все-таки имеет смысл?
Да, когда несколько процессов - supervisor или entrypoint.sh



### Вызов kube-proxy как бинаря

Можно делать прямо так `k -n kube-system exec kube-proxy-h8nlf  -- kube-proxy --help`.
Здесь можно увидеть какие возомжности есть у куб прокси как логической единицы.

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

### ClusterIP
* ClusterIP выделяет IP-адрес для каждого сервиса из особого диапазона (этот адрес виртуален и даже не настраивается на сетевых интерфейсах)
* Когда pod внутри кластера пытается подключиться к виртуальному IP-адресу сервиса, то node, где запущен pod, меняет адрес получателя в сетевых пакетах на настоящий адрес pod-а.
* Нигде в сети, за пределами ноды, виртуальный ClusterIP не существует.

> IP-адрес для каждого сервиса из особого диапазона
> (этот адрес виртуален и даже не настраивается на сетевых интерфейсах)

Every node in a Kubernetes cluster runs a kube-proxy. kube-proxy is responsible for implementing a form of virtual IP for Services of type other than ExternalName.

То есть это функционал типа dnat, который заменяет виртуальный ip ClusterIP > Target Pod IP.
Соответственно с физических нод этот IP не должен пинговаться - он хранится только в цепочках iptables.

Вот он
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

**SEP** - Service Endpoint

**Но!**
В случае работы через ipvs, а не iptables, clusterIP записывается на сетевой интерфейс и перестаёт быть виртуальным адресом и его можно пинговать!
При этом правила в iptables построены по-другому. Вместо цепочки правил для каждого сервиса, теперь используются хэш-таблицы (ipset). Можно посмотреть их, установив утилиту ipset.

То есть в iptables хранится минимум - основная инфа по правилам, а в быстрых хэш-таблицах, которые как раз хорошо работают при большом количестве нод - ip-адреса endpoint-ов.

```
iptables --list -nv -t nat
ip addr show kube-ipvs0
ipset list
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

### Upgrade UDP > TCP localDNS

В localDNS, который располагается на ноде и кеширует соответствие, используется upgrade to tcp (from udp), чтобы располагаясь за NATом запросы не терялись.

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




## IPVS
IPVS (IP Virtual Server) implements transport-layer load balancing, usually called Layer 4 LAN switching, as part of Linux kernel.

IPVS runs on a host and acts as a load balancer in front of a cluster of real servers. IPVS can direct requests for TCP and UDP-based services to the real servers, and make services of real servers appear as virtual services on a single IP address.

Разница в балансировке сервисов между iptables и ipvs следующая. Допустим 3 пода, на которые может уходить трафик с сервиса:
* iptables: последовательная цепочка правил 0.33 * ip pod1 > 0.5 * pod2 > pod3 - И эти вероятности выбора пода динамически изменяются в зависимости от масштабирования.
* ipvs: изначально балансер и в него вшит менее топорный механизм балансировки (least load, least connections, locality, weighted, etc. http://www.linuxvirtualserver.org/docs/scheduling.html) и достаточно добавить ip нового пода, а не обновлять правила каждый раз.
Причём для балансера создаётся виртуальный сетевой интерфейс, на котором будут все адреса подов, которые подходят сервису.
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
Вместо цепочки правил для каждого сервиса, теперь используются хэш-таблицы (ipset). Можно посмотреть их используя `ipset list`.
```
Name: KUBE-CLUSTER-IP
Type: hash:ip,port
Revision: 5
Header: family inet hashsize 1024 maxelem 65536
Size in memory: 640
References: 2
Number of entries: 7
Members:
10.102.189.119,tcp:80
10.96.0.10,tcp:53
10.96.0.10,udp:53
10.100.124.99,tcp:80
10.96.0.10,tcp:9153
10.96.0.1,tcp:443
10.100.114.194,tcp:8000
```

#### Snippet for enabling IPVS mode, cleaning up routing rules and creating new route
```
kubectl get configmap kube-proxy -n kube-system -o yaml | \
  sed -e "s/mode: \"\"/mode: \"ipvs\"/" | \
  kubectl apply -f - -n kube-system
kubectl get configmap kube-proxy -n kube-system -o yaml | \
  sed -e "s/strictARP: false/strictARP: true/" | \
  kubectl apply -f - -n kube-system

kubectl --namespace kube-system delete pod --selector='k8s-app=kube-proxy'

minikube ssh "sudo -i"
sed -i "s/nameserver 192.168.49.1/nameserver 192.168.49.1\nnameserver 1.1.1.1/g" /etc/resolv.conf > /etc/resolv.conf.new
mv /etc/resolv.conf.new /etc/resolv.conf

cat <<EOF >> /tmp/iptables.cleanup
*nat
-A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE
COMMIT
*filter
COMMIT
*mangle
COMMIT
EOF
iptables-restore /tmp/iptables.cleanup

sudo ip route add 172.17.255.0/24 via 192.168.49.2
```