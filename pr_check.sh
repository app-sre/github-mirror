#!/bin/bash

IMAGE_TEST=ghmirror-test

docker build -t ${IMAGE_TEST} -f Dockerfile .
docker run --rm ${IMAGE_TEST}
