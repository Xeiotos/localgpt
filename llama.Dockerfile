# Build stage
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    mkdir build && \
    cd build && \
    cmake .. -DGGML_CUDA=ON && \
    cmake --build . --config Release -j$(nproc)

# Runtime stage
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/llama.cpp/build/bin/llama-server /app/llama-server

EXPOSE 8502

ENTRYPOINT ["./llama-server"]