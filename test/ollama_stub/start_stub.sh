#!/bin/bash

DIRNAME=$(dirname "$0")
pushd $DIRNAME
docker build -t "fauxllama" .
docker run -d --name 'fauxllama' -p 11404:11404 'fauxllama' 
popd