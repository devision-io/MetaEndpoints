from metasdk.tools import exec_cmd


def run_esp_init():
    """
    Подготавливает машину разработчика к дальнейшей работе.
    Запустить один раз
    """
    exec_cmd('docker run -ti --name gcloud-config google/cloud-sdk:220.0.0-alpine gcloud auth login')


if __name__ == '__main__':
    run_esp_init()
