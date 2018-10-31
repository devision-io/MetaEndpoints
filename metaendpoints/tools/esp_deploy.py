import argparse

from metasdk import read_developer_settings
from metasdk.tools import exec_cmd


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

    run_esp_deploy(lang, service, workdir)


def run_esp_deploy(lang, service, workdir):
    gcloud_params = read_developer_settings().get('gcloudDev')
    if not gcloud_params:
        raise ValueError("gcloudDev не установлены в developer_settings")
    gcloud_project = gcloud_params['project']
    gcloud_prefix = gcloud_params.get('prefix', '')
    gen_stubs_and_deploy(service, lang, workdir, gcloud_project, gcloud_prefix)


def gen_stubs_and_deploy(service: str, lang: str, workdir: str, gcloud_project: str, gcloud_prefix: str):
    exec_cmd("""
    docker run --rm \
        --volumes-from gcloud-config \
        -v {workdir}:/app_source \
        -v /mnt/static:/mnt/static \
        apisgarpun/apiservice-deploy:latest \
        --service={service} \
        --lang={lang} \
        --gcloud_project={gcloud_project} \
        --gcloud_prefix={gcloud_prefix}
    """.format(
        workdir=workdir,
        service=service,
        lang=lang,
        gcloud_project=gcloud_project,
        gcloud_prefix=gcloud_prefix
    ))


if __name__ == '__main__':
    main()
