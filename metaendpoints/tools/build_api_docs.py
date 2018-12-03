import argparse
import json
import shutil
from os import scandir, remove
from os.path import join

import yaml

from metaendpoints.tools import exec_cmd

REQUIRED_PH = 'Обязательно.'

swagger2markup_content = """
# https://github.com/Swagger2Markup/swagger2markup/blob/master/src/docs/asciidoc/usage_guide.adoc
swagger2markup.markupLanguage=MARKDOWN

#swagger2markup.separatedDefinitionsEnabled=true
#swagger2markup.separatedOperationsEnabled=true
#swagger2markup.anchorPrefix=anchorPrefix

swagger2markup.pathsGroupedBy=TAGS
#swagger2markup.generatedExamplesEnabled=true
swagger2markup.outputLanguage=RU
swagger2markup.inlineSchemaEnabled=true
swagger2markup.interDocumentCrossReferencesEnabled=true
swagger2markup.interDocumentCrossReferencesPrefix=xrefPrefix
swagger2markup.flatBodyEnabled=false
swagger2markup.pathSecuritySectionEnabled=false

swagger2markup.listDelimiter=|
swagger2markup.listDelimiterEnabled=true
swagger2markup.tagOrderBy=AS_IS
swagger2markup.operationOrderBy=AS_IS
swagger2markup.definitionOrderBy=AS_IS
swagger2markup.parameterOrderBy=AS_IS
swagger2markup.propertyOrderBy=AS_IS
swagger2markup.responseOrderBy=AS_IS
"""

import re


def underscore_to_camelcase(s):
    return re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)


def get_service_conf(api_workdir, service):
    conf_path = api_workdir + "/" + service + ".yaml"
    with open(conf_path, 'r') as f:
        return yaml.load(f.read())


def build_doc(service, workdir):
    print("Build docs...")
    api_workdir = join(workdir, "api")
    proto_path = join(api_workdir, "proto")

    versions = []
    for entry in scandir(proto_path):
        versions.append(entry.name)

    for version in versions:
        version_dir = join(proto_path, version)
        build_swagger(service, version_dir)

        doc_content = get_gen_doc_content(join(version_dir, "doc_json.json"),
                                          service)
        swagger_file = service + ".swagger.json"
        file = join(version_dir, swagger_file)
        with (open(file, 'r'))as f:
            sw_str = f.read()
            sw_str = sw_str.replace('"' + version, '"')
            sw_str = sw_str.replace('#/definitions/' + version, '#/definitions/')
            swagger = json.loads(sw_str)
        swagger['info']['version'] = None
        swagger['info'].pop('version')

        swagger['host'] = service + '.apis.devision.io'
        swagger['schemes'] = ["http"]

        swagger['schemes'] = None
        swagger['consumes'] = None
        swagger['produces'] = None
        swagger['tags'] = []
        for srv in doc_content['services']:
            swagger['tags'].append({
                "name": srv['name'],
                "description": srv['description'],
            })
        for defK, defV in swagger['definitions'].items():
            print(defK)

            required = []

            for fK, fV in defV.get('properties', {}).items():
                title = fV.get('title')
                description = fV.get('description')

                if not title and not description:
                    raise ValueError("Нет комментария поля: " + str(fK))

                if not title and description:
                    parts = description.split("\n")
                    if parts:
                        title = parts[0]

                if REQUIRED_PH in title:
                    required.append(fK)
                    title = title.replace(REQUIRED_PH, '').strip()

                alternative_name = underscore_to_camelcase(fK)
                if alternative_name != fK:
                    title += "\nАльтернативное имя: " + alternative_name

                if not description:
                    fV['description'] = title
                if 'type' in fV and fV['type'] == 'array' \
                        and fV['items'].get('format') == 'int64':
                    fV['items']['type'] = 'number'
            defV['required'] = required
        with (open(file, 'w'))as f:
            f.write(json.dumps(swagger))

        target = join(workdir, "docs", "content", "api",
                      version + "_" + swagger_file)
        shutil.move(file, target)


def get_gen_doc_content(doc_json, service):
    service__proto_ = service + ".proto"
    try:
        with (open(doc_json, 'r'))as f:
            con_ = json.loads(f.read())
            for f in con_['files']:
                if f['name'] == service__proto_:
                    return f
    finally:
        remove(doc_json)
    raise ValueError("В результатах генериации документации не найден файл: " + service__proto_)


def build_swagger(service, version_dir):
    exec_cmd("""
        docker run --rm \
            -v {version_dir}:{version_dir} \
            -w {version_dir} \
            znly/protoc:0.3.0 \
            -I. --swagger_out=logtostderr=true:. \
            --doc_out=./ \
            --doc_opt=json,doc_json.json \
            {service}.proto
        """.format(
        version_dir=version_dir,
        service=service,
    ))


def build_markdown(swagger_file, version_dir, version):
    exec_cmd("""
        docker run --rm \
            -v {version_dir}:/opt \
            swagger2markup/swagger2markup convert \
            -i /opt/{swagger_file} -f /opt/out/reference/api/{version}/_index -c /opt/config.properties
        """.format(
        version_dir=version_dir,
        version=version,
        swagger_file=swagger_file,
    ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--service', help='Name of API Service. Example: hello', type=str, required=True)
    parser.add_argument('--workdir', help='Root of project dir. Default "."', default=".", type=str, required=False)
    args = parser.parse_args()
    build_doc(args.service, args.workdir)


if __name__ == '__main__':
    main()
