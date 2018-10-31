#!/usr/bin/env python3

import argparse
import os
import subprocess


def exec_cmd(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check)


workdir = "/app_source"
api_workdir = workdir + "/api"
proto_path = api_workdir + "/proto"
build_dir = workdir + "/build"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', help='Имя API Сервиса. Например: hello', type=str, required=True)
    parser.add_argument('--lang', help='Язык для которого генерируется код. Например: python', type=str, required=True)
    parser.add_argument('--gcloud_project', help='Имя проекта Google Cloud для которого идет билд', type=str, required=True)
    parser.add_argument('--gcloud_prefix', help='Опционально. Префикс разработчика для разделение билдов в одном проекте', type=str, required=False, default="")
    args = parser.parse_args()

    if not os.path.exists(build_dir):
        os.mkdir(build_dir)

    service_protos = gen_stubs(args)

    gen_gcloud_confs(service_protos, args)


def gen_stubs(args):
    versions = []
    for entry in os.scandir(proto_path):
        versions.append(entry.name)
    service_protos = []
    for api_version in versions:
        proto_file_path = api_workdir + "/proto/" + api_version + "/" + args.service + ".proto"
        service_protos.append(proto_file_path)

        if args.lang == 'python':
            gen_dir = workdir + "/src/"
            if not os.path.exists(gen_dir):
                os.makedirs(gen_dir)

            exec_cmd("""
                    python3 -m grpc.tools.protoc \
                        --proto_path={proto_path} \
                        --proto_path=/api-common-protos \
                        --python_out={gen_dir} \
                        --mypy_out={gen_dir} \
                        --grpc_python_out={gen_dir} \
                        {proto_file_path}
                """.format(
                api_version=api_version,
                proto_path=proto_path,
                proto_file_path=proto_file_path,
                gen_dir=gen_dir
            ))
        else:
            raise ValueError("Not supported command argument: language ")
    return service_protos


def gen_gcloud_confs(service_protos, args):
    api_descriptor_path = build_dir + "/api_descriptor.pb"

    exec_cmd("""
            python3 -m grpc.tools.protoc \
                --include_imports \
                --include_source_info \
                --proto_path={proto_path} \
                --proto_path=/api-common-protos \
                --descriptor_set_out={api_descriptor_path} \
                {proto_file_paths}
        """.format(
        proto_path=proto_path,
        proto_file_paths=' '.join(service_protos),
        api_descriptor_path=api_descriptor_path
    ))

    conf_path = api_workdir + "/" + args.service + ".yaml"
    with open(conf_path, 'r') as f:
        endpoint_service_name = args.gcloud_prefix + "-" + args.service if args.gcloud_prefix else args.service

        config_content = f.read()
        config_content = config_content.replace("$SERVICE_ID", endpoint_service_name)
        config_content = config_content.replace("$PROJECT_ID", args.gcloud_project)

        endpoint_conf = build_dir + "/endpoint_conf.yaml"  # "/tmp/out.yaml"
        with open(endpoint_conf, 'w') as f:
            f.write(config_content)

    exec_cmd('gcloud endpoints services deploy {api_descriptor_path} {endpoint_conf} --project {project}'.format(
        endpoint_conf=endpoint_conf,
        api_descriptor_path=api_descriptor_path,
        project=args.gcloud_project
    ))


if __name__ == '__main__':
    main()
