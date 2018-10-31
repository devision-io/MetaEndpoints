# docker run -ti --name gcloud-config google/cloud-sdk:220.0.0-slim gcloud auth login

docker build -t apisgarpun/apiservice-deploy:latest .
docker push apisgarpun/apiservice-deploy:latest
