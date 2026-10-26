#!/bin/bash

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found"
    exit 1
fi

# echo "$MODEL | $API_KEY"

# llama-server -hf Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M \
#   -c 4096 \
#   -ngl 99 \
#   -b 512 \
#   -ub 512 \
#   -fa on \
#   --host 127.0.0.1 \
#   --port 8080

llama serve -hf $MODEL \
  -c 4096 \
  -ngl 99 \
  -ctk q8_0 \
  -ctv q8_0 \
  --reasoning off \
  --host 127.0.0.1 \
  --port 8080 \
  --api-key $API_KEY
