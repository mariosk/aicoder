#!/bin/bash

DOCKER_COMPOSE="docker-compose --env-file .env.staging -f docker-compose.yml"

function usage()
{
    echo "$0 [ start | stop | restart | clean ]"
}

function exec_cmd()
{
    echo $@
    eval $@
}

function start()
{
    COMMAND="$DOCKER_COMPOSE up -d $1"
    exec_cmd $COMMAND
}

function stop()
{
    COMMAND="$DOCKER_COMPOSE stop $1"
    exec_cmd $COMMAND
}

function clean()
{
    COMMAND="$DOCKER_COMPOSE rm -f $1"
    exec_cmd $COMMAND
    rm -rf /var/lib/$1
}

if [ $# -ne 1 ];
then
    usage
    exit 1
fi

for container_name in $(cat .CONTAINER_NAME)
do

    if [ "$1" == "start" ]
    then
        start $container_name
    elif [ "$1" == "stop" ]
    then
        stop $container_name
    elif [ "$1" == "clean" ]
    then
        stop $container_name
        clean $container_name
    elif [ "$1" == "restart" ]
    then
        stop $container_name
        start $container_name
    else
        usage
        exit 2
    fi
done

docker system prune -f
docker ps -a
