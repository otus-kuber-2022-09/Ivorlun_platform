#! /usr/bin/env python3
import base64
from datetime import datetime
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
def mysql_on_create(body, namespace, logger, **kwargs):
    name = body['metadata']['name']
    image = body['spec']['image']
    password = base64.b64encode(bytes(body['spec']['password'], "ascii")).decode("ascii")
    database = body['spec']['database']
    storage_size = body['spec']['storage_size']
    storage_class = body['spec']['storage_class']
    namespace = namespace

    logger.info(f"Creating CRD called {name} within {namespace} namespace")
    # Генерируем JSON манифесты для деплоя
    secret = render_template('mysql-secret.yml.j2',
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
    # Создаем mysql SVC:
    mysql_svc = api.create_namespaced_service(namespace, service)
    # Создаем mysql Secret:
    mysql_secret = api.create_namespaced_secret(namespace, secret)
    # Создаем mysql PV:
    mysql_pv = api.create_persistent_volume(persistent_volume)
    # Создаем mysql PVC:
    mysql_pvc = api.create_namespaced_persistent_volume_claim(namespace, persistent_volume_claim)

    # Создаем mysql Deployment:
    api = kubernetes.client.AppsV1Api()
    mysql_deployment = api.create_namespaced_deployment(namespace, deployment)


    # Пытаемся восстановиться из backup
    try:
        api = kubernetes.client.BatchV1Api()
        mysql_restore_job = api.create_namespaced_job(namespace, restore_job)
    except kubernetes.client.rest.ApiException:
        pass

    # Cоздаем PVC и PV для бэкапов:
    try:
        backup_pv = render_template('backup-pv.yml.j2', {'name': name,
                                                        'storage_size': storage_size,
                                                        'storage_class': storage_class})
        api = kubernetes.client.CoreV1Api()
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
            'mysql_secret': mysql_secret.metadata.name,
            'mysql_pv': mysql_pv.metadata.name,
            'mysql_pvc': mysql_pvc.metadata.name,
            'mysql_svc': mysql_svc.metadata.name,
            'mysql_restore_job': mysql_restore_job.metadata.name
            }


@kopf.on.delete('otus.homework', 'v1', 'mysqls')
def delete_object_make_backup(body, status, namespace, logger, **kwargs):
    namespace = namespace
    name = body['metadata']['name']
    image = body['spec']['image']
    database = body['spec']['database']

    cr_deployment_name = status['mysql_on_create']['mysql_deployment']

    delete_success_jobs(name, namespace)
    logger.info(f"Creating bkp job for: {name}")

    # Cоздаем backup job:
    backup_job = render_template('backup-job.yml.j2', {
        'name': name,
        'image': image,
        'database': database})

    try:
        api = kubernetes.client.AppsV1Api()
        api.read_namespaced_deployment(cr_deployment_name, namespace)
        try:
            api = kubernetes.client.BatchV1Api()
            api.create_namespaced_job(namespace, backup_job)
            wait_until_job_end(f"backup-{name}-job", namespace)
            return {'message': "Backup finished. Mysql and its children resources deleted"}
        except kubernetes.client.rest.ApiException as e:
            print("Exception when calling AppsV1Api->read_namespaced_deployment: %s\n" % e)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling AppsV1Api->read_namespaced_deployment: %s\n" % e)
        logger.info(f"No backup because no CR Deployment with name: {cr_deployment_name}")
        pass
    return {'message': "No backup was accomplished"}


@kopf.on.update('otus.homework', 'v1', 'mysqls')
def mysql_on_update(name, body, status, namespace, logger, **kwargs):

    logger.info(f"HERE STARTS mysql_on_update and delete_object_make_backup upcoming")

    delete_object_make_backup(body, status, namespace, logger, **kwargs)
    logger.info(f"delete_object_make_backup finished")
    logger.info(f"obtaing resources names from status")

    cr_deployment_name = status['mysql_on_create']['mysql_deployment']
    cr_secret_name = status['mysql_on_create']['mysql_secret']
    cr_pv_name = status['mysql_on_create']['mysql_pv']
    cr_pvc_name = status['mysql_on_create']['mysql_pvc']
    cr_svc_name = status['mysql_on_create']['mysql_svc']
    cr_restore_job_name = status['mysql_on_create']['mysql_restore_job']

    logger.info(f"Going to delete every resource")

    try:
        api = kubernetes.client.AppsV1Api()
        api_response = api.delete_namespaced_deployment(cr_deployment_name, namespace)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling AppsV1Api->delete_namespaced_deployment: %s\n" % e)

    try:
        api = kubernetes.client.BatchV1Api()
        api_response = api.delete_namespaced_job(cr_restore_job_name, namespace)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_job: %s\n" % e)

    api = kubernetes.client.CoreV1Api()
    try:
        api_response = api.delete_namespaced_secret(cr_secret_name, namespace)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_secret: %s\n" % e)

    try:
        api_response = api.delete_namespaced_persistent_volume_claim(cr_pvc_name, namespace)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_persistent_volume_claim: %s\n" % e)

    try:
        api_response = api.delete_namespaced_service(cr_svc_name, namespace)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->delete_namespaced_service: %s\n" % e)

    try:
        api_response = api.delete_persistent_volume(cr_pv_name)
        print(api_response)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->delete_persistent_volume: %s\n" % e)

    logger.info(f"Checking persistent volume is removed")
    try:
        api_response = api.read_persistent_volume(cr_pv_name)
        print(api_response)
        time.sleep(20)
    except kubernetes.client.rest.ApiException as e:
        print("Exception when calling CoreV1Api->read_persistent_volume: %s\n" % e)
        pass


    logger.info(f"Going to recreate all resources via mysql_on_create")

    mysql_on_create(body, namespace, logger, **kwargs)
    logger.info(f"Object is updated: {name}")
