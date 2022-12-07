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

Механизм, при котором запросы снаружи до reverse-proxy идут как обычно шифрованные, но уже от reverse-proxy до приложения идут без шифрования трафика.

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
1. Приходит на внешний ip-адрес MetalLB балансировщика nginx-ingress LoadBalancer Service
1. Из балансировщика перенаправляется в nginx-ingress-controller pod
1. Из ingress-а запрос уходит на нужный ClusterIP сервис, который указан в rules и backend-е
1. Из ClusterIP сервиса уже попадает в целевые pod-ы


## Ephemeral Containers

Since Pods are just groups of semi-fused containers and the isolation between containers in a Pod is weakened, such a new container could be used to inspect the other containers in the (acting up) Pod regardless of their state and content.

And that's how we get to the idea of an Ephemeral Container - "a special type of container that runs temporarily in an existing Pod to accomplish user-initiated actions such as troubleshooting."

k debug -n <namespace> <pod-to-debug> --image=busybox

https://iximiuz.com/en/posts/kubernetes-ephemeral-containers/

## Debugging pods!

1. kubectl describe
1. kubectl get events
1. kubectl logs
1. kubectl exec -it <pod> -- sh
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
```
spec:
  rules:
  - http:
      paths:
      - path: /dashboard
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
