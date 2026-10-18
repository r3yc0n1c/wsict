#!/bin/bash

llama-server -hf Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M \
  -c 4096 \
  -ngl 99 \
  -b 512 \
  -ub 512 \
  -fa on \
  --host 127.0.0.1 \
  --port 8080
