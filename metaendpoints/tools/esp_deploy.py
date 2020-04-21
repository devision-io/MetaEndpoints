import os
import argparse
import hashlib
from os import scandir
from os.path import join

from metasdk import read_developer_settings
from metasdk.internal import OS_NAME

from metaendpoints.tools import exec_cmd
from metaendpoints.tools.build_api_docs import build_doc


def main():
    """
    Заливает конфигурацию в Google Cloud Endpoints
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', help='Name of API Service. Example: hello', type=str, required=True)
    parser.add_argument('--lang', help='For each language generating code. Example: python', type=str, required=True)
    parser.add_argument('--workdir', help='Root of project dir. Default "."', default=".", type=str, required=False)
    args = parser.parse_args()

    workdir = args.workdir
    service = args.service
    lang = args.lang

    build_doc(service, workdir)
    run_esp_deploy(lang, service, workdir)


def md5_file(service, workdir):
    api_workdir = join(workdir, "api")
    proto_path = join(api_workdir, "proto")

    versions = []
    for entry in scandir(proto_path):
        versions.append(entry.name)

    for version in versions:
        version_dir = join(proto_path, version)
        input_file_name = join(version_dir, service + ".proto")
        md5_file_name = join(version_dir, service + "_md5")

        hash_md5 = hashlib.md5()
        with open(input_file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)

        with open(md5_file_name, "w") as f:
            f.write(hash_md5.hexdigest())


def run_esp_deploy(lang, service, workdir):
    print("Code generation and deploy ESP config...")

    gcloud_params = read_developer_settings().get('gcloudDev')
    if not gcloud_params:
        raise ValueError("gcloudDev не установлены в developer_settings")
    gcloud_project = gcloud_params['project']
    gcloud_prefix = gcloud_params.get('prefix', '')
    gen_stubs_and_deploy(service, lang, workdir, gcloud_project, gcloud_prefix)


def gen_stubs_and_deploy(service: str, lang: str, workdir: str, gcloud_project: str, gcloud_prefix: str):
    """
    Генерация исходного кода классов-заглушек в коде проекта, генерация esp конфигурации и деплой в google cloud endpoints
    """

    docker_user = ""
    if OS_NAME == "linux":
        # чтобы файлы не создавались из под рута
        docker_user = "--user " + str(os.getuid()) + ":" + str(os.getgid())
        build_dir = "/mnt/static"
    else:
        # на macos и win очень сложно создать /mnt/static и подмаунтить ее в докер
        # а на проде linux и на десктопе с этим тоже нет проблем
        from metasdk.internal import __build_path
        build_dir = __build_path("/.rwmeta/.espbuild")
        os.makedirs(build_dir, exist_ok=True)

    exec_cmd("""
    docker run --rm \
        {docker_user} --volumes-from gcloud-config \
        -v {workdir}:/app_source \
        -v {build_dir}:/mnt/static \
        apisgarpun/apiservice-deploy:latest \
        --service={service} \
        --lang={lang} \
        --gcloud_project={gcloud_project} \
        --gcloud_prefix={gcloud_prefix}
    """.format(
        docker_user=docker_user,
        workdir=workdir,
        build_dir=build_dir,
        service=service,
        lang=lang,
        gcloud_project=gcloud_project,
        gcloud_prefix=gcloud_prefix
    ))

    md5_file(service, workdir)


if __name__ == '__main__':
    main()
