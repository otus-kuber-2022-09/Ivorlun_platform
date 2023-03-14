#! /usr/bin/env python3
import base64
from jinja2 import Environment, FileSystemLoader
import kopf
import kubernetes
import time
import yaml


def render_template(filename, vars_dict):
    env = Environment(loader=FileSystemLoader('./templates'))
    template = env.get_template(filename)
    yaml_manifest = template.render(vars_dict)
    json_manifest = yaml.load(yaml_manifest, Loader=yaml.FullLoader)
    return json_manifest

def wait_until_job_end(jobname, namespace):
    api = kubernetes.client.BatchV1Api()
    job_finished = False
    jobs = api.list_namespaced_job(namespace)
    while (not job_finished) and \
            any(job.metadata.name == jobname for job in jobs.items):
        time.sleep(1)
        jobs = api.list_namespaced_job(namespace)
        for job in jobs.items:
            if job.metadata.name == jobname:
                print(f"job with { jobname }  found,wait untill end")
                if job.status.succeeded == 1:
                    print(f"job with { jobname }  success")
                    job_finished = True

def delete_success_jobs(mysql_instance_name, namespace):
    print("start deletion")
    api = kubernetes.client.BatchV1Api()
    jobs = api.list_namespaced_job(namespace)
    for job in jobs.items:
        jobname = job.metadata.name
        if (jobname == f"backup-{mysql_instance_name}-job") or \
                (jobname == f"restore-{mysql_instance_name}-job"):
            if job.status.succeeded == 1:
                api.delete_namespaced_job(jobname,
                                            namespace,
                                            propagation_policy='Background')


@kopf.on.create('otus.homework', 'v1', 'mysqls')
# Функция, которая будет запускаться при создании объектов тип MySQL:
def mysql_on_create(body, namespace, spec, **kwargs):
    name = body['metadata']['name']
    image = body['spec']['image']
    password = base64.b64encode(b"{body['spec']['password']}").decode("ascii")
    database = body['spec']['database']
    storage_size = body['spec']['storage_size']
    storage_class = body['spec']['storage_class']
    namespace = namespace

    # Генерируем JSON манифесты для деплоя
    secret = render_template('mysql-pass.yml.j2',
                                        {'name': name,
                                        'password': password})
    persistent_volume = render_template('mysql-pv.yml.j2',
                                        {'name': name,
                                        'storage_size': storage_size,
                                        'storage_class': storage_class})
    persistent_volume_claim = render_template('mysql-pvc.yml.j2',
                                                {'name': name,
                                                'storage_size': storage_size,
                                                'storage_class': storage_class})
    service = render_template('mysql-service.yml.j2', {'name': name})

    deployment = render_template('mysql-deployment.yml.j2', {
        'name': name,
        'image': image,
        'database': database})
    restore_job = render_template('restore-job.yml.j2', {
        'name': name,
        'image': image,
        'database': database})

    # Определяем, что созданные ресурсы являются дочерними к управляемому CustomResource:
    kopf.append_owner_reference(persistent_volume, owner=body)
    kopf.append_owner_reference(persistent_volume_claim, owner=body)
    kopf.append_owner_reference(service, owner=body)
    kopf.append_owner_reference(deployment, owner=body)
    kopf.append_owner_reference(restore_job, owner=body)
    kopf.append_owner_reference(secret, owner=body)
    # ^ Таким образом при удалении CR удалятся все, связанные с ним pv,pvc,svc, deployments

    api = kubernetes.client.CoreV1Api()
    mysql_pass = api.create_namespaced_secret(namespace, secret)
    # Создаем mysql PV:
    api.create_persistent_volume(persistent_volume)
    # Создаем mysql PVC:
    api.create_namespaced_persistent_volume_claim(namespace, persistent_volume_claim)
    # Создаем mysql SVC:
    api.create_namespaced_service(namespace, service)

    # Создаем mysql Deployment:
    api = kubernetes.client.AppsV1Api()
    mysql_deployment = api.create_namespaced_deployment(namespace, deployment)


    # Пытаемся восстановиться из backup
    try:
        api = kubernetes.client.BatchV1Api()
        api.create_namespaced_job(namespace, restore_job)
    except kubernetes.client.rest.ApiException:
        pass

    # Cоздаем PVC и PV для бэкапов:
    try:
        backup_pv = render_template('backup-pv.yml.j2', {'name': name,
                                                        'storage_size': storage_size,
                                                        'storage_class': storage_class})
        api = kubernetes.client.CoreV1Api()
        print(api.create_persistent_volume(backup_pv))
        api.create_persistent_volume(backup_pv)
    except kubernetes.client.rest.ApiException:
        pass

    try:
        backup_pvc = render_template('backup-pvc.yml.j2', {'name': name,
                                                            'storage_size': storage_size,
                                                            'storage_class': storage_class})
        api = kubernetes.client.CoreV1Api()
        api.create_namespaced_persistent_volume_claim(namespace, backup_pvc)
    except kubernetes.client.rest.ApiException:
        pass

    return {'mysql_deployment': mysql_deployment.metadata.name,
            'mysql_pass': mysql_pass.metadata.name}


@kopf.on.delete('otus.homework', 'v1', 'mysqls')
def delete_object_make_backup(body, namespace, logger, **kwargs):
    namespace = namespace
    name = body['metadata']['name']
    image = body['spec']['image']
    database = body['spec']['database']

    delete_success_jobs(name, namespace)
    logger.info(f"Creating bkp job for: {name}")

    # Cоздаем backup job:
    api = kubernetes.client.BatchV1Api()
    backup_job = render_template('backup-job.yml.j2', {
        'name': name,
        'image': image,
        'database': database})
    api.create_namespaced_job(namespace, backup_job)
    wait_until_job_end(f"backup-{name}-job", namespace)
    return {'message': "mysql and its children resources deleted"}


@kopf.on.update('otus.homework', 'v1', 'mysqls')
def mysql_on_update(spec, status, namespace, logger, **kwargs):

    password = base64.b64encode(spec.get('password', None)).decode("ascii")
    if not password:
        raise kopf.PermanentError(f"password must be set. Got {password!r}.")

    secret_name = status['mysql_on_create']['mysql_pass']
    secret_patch = {'data': {'password': password}}

    api = kubernetes.client.CoreV1Api()
    mysql_secret = api.patch_namespaced_secret(
        namespace=namespace,
        name=secret_name,
        body=secret_patch,
    )

    logger.info(f"Object is updated: {mysql_secret}")

    # mysql_deployment_name = status['mysql_on_create']['mysql_deployment']
    # logger.info(f"Going to restart deployment: {mysql_on_create}")
    # Интересно, если секрет поменяется, то перезапустится ли деплоймент сам?

    return {'Object secret has been updated': mysql_secret.metadata.name}
