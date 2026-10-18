#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: ./llama.sh <model-name>"
    echo -e "e.g. \n\n./llama.sh Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M"
    exit 1
fi

#   -c 4096 \             # Context size
#   -ngl 99 \             # GPU layer offloading - offload up to 99 layers
#   -b 512 \              # Logical batch size
#   -ub 512 \             # Physical or micro-batch size
#   -fa on \              # Flash Attention

llama-server -hf $1 \
  -c 4096 \
  -ngl 99 \
  -b 512 \
  -ub 512 \
  -fa on \
  --host 127.0.0.1 \
  --port 8080
