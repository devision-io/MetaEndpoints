import argparse
from os.path import expanduser

from metasdk import read_developer_settings
from metasdk.internal import OS_NAME
from metaendpoints.tools import exec_cmd


def main():
    """
    Запускает локальный Docker контейнер с google cloud esp
    Это нужно для транскодирования REST запросов на ваш GRPC backend, а так же проверки авторизации
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', help='Name of API Service. Example: hello', type=str, required=True)
    parser.add_argument('--backend_port', help='Backend grpc app port. Default: 50051', type=int, required=False, default=50051)
    parser.add_argument('--frontend_http_port', help='ESP Frontend port for HTTP(REST) requests. Default: 8083', type=int, required=False, default=8083)
    parser.add_argument('--frontend_grpc_port', help='ESP Frontend port for GRPC request. Default: 8084', type=int, required=False, default=8084)
    parser.add_argument('--service_account_key_file', help='Service account json file for trace and log google cloud api. Default: test-esp-service-account-creds.json', type=str,
                        required=False, default="test-esp-service-account-creds.json")
    args = parser.parse_args()

    grpc_service = args.service
    frontend_http_port = args.frontend_http_port
    backend_port = args.backend_port
    frontend_grpc_port = args.frontend_grpc_port

    run_serve(grpc_service, backend_port, frontend_http_port, frontend_grpc_port)


def run_serve(grpc_service, backend_port=50051, frontend_http_port=8083, frontend_grpc_port=8084):
    """
    Запуск nginx esp для проксирования и транскодирования http -> grpc
    """
    gcloud_params = read_developer_settings().get('gcloudDev')
    if not gcloud_params:
        raise ValueError("gcloudDev не установлены в developer_settings")
    gcloud_project = gcloud_params['project']
    gcloud_prefix = gcloud_params.get('prefix', '')
    endpoint_service_name = gcloud_prefix + "-" + grpc_service if gcloud_prefix else grpc_service
    user_dir = expanduser("~")

    ext_params = ""
    if OS_NAME == "macos":
        backend_host = "docker.for.mac.localhost"
    elif OS_NAME == "windows":
        backend_host = "docker.for.win.localhost"
    else:
        backend_host = "localhost"
        ext_params = "--network=host"
    print("Start proxy server on: http://localhost:" + str(frontend_http_port))
    exec_cmd("""
        docker run \
            --rm {ext_params} \
            --publish={frontend_http_port}:{frontend_http_port} \
            --publish={frontend_grpc_port}:{frontend_grpc_port} \
            --volume={user_dir}/.rwmeta:/esp \
            gcr.io/endpoints-release/endpoints-runtime:1 \
            --service={endpoint_service_name}.endpoints.{project}.cloud.goog \
            --rollout_strategy=managed \
            --http_port={frontend_http_port} \
            --http2_port={frontend_grpc_port} \
            --backend=grpc://{backend_host}:{backend_port} \
            --service_account_key=/esp/test-esp-service-account-creds.json
        """.format(
        ext_params=ext_params,
        user_dir=user_dir,
        backend_port=backend_port,
        frontend_grpc_port=frontend_grpc_port,
        frontend_http_port=frontend_http_port,
        backend_host=backend_host,
        project=gcloud_project,
        endpoint_service_name=endpoint_service_name
    ))


if __name__ == '__main__':
    main()
