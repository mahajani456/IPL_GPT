#!/usr/bin/env bash

gunicorn app:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080