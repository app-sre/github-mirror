#!/bin/bash

IMAGE_TEST=ghmirror-test

docker build -t ${IMAGE_TEST} -f Dockerfile --target test .
