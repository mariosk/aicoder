#!/bin/bash

source app/common.sh

function usage()
{
    echo "$0 [ local | prod | clean ]"
}

function build()
{
    find . -name "__pycache__" -exec rm -rf {} \;
    find . -name "*.pyc" -exec rm -rf {} \;
    update_git_commit_hash
    rm -rf ./huggingface_cache
    cp -r $HOME/.cache/huggingface ./huggingface_cache
    DOCKER_BUILDKIT=1 docker build --progress=plain -t aicoder-base -f Dockerfile.base .
    DOCKER_BUILDKIT=1 docker build --progress=plain -t $(cat .CONTAINER_NAME) -f Dockerfile .
}

if [ $# -ne 1 ];
then
    usage
    exit 1
fi

for container_name in $(cat .CONTAINER_NAME)
do
    if [ "$1" == "local" ]
    then
        build $container_name
    elif [ "$1" == "prod" ]
    then
        build $container_name
    elif [ "$1" == "clean" ]
    then
        docker rm -f $container_name
        docker rmi -f $(docker images | grep $container_name | awk -F" " '{print $3}')
        docker images | grep $container_name
    fi
    docker system prune -f
done
