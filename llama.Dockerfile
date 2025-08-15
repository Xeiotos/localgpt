# Build stage
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    libcurl4-openssl-dev \
    pkg-config \
    wget \
    ccache \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    mkdir build && \
    cd build && \
    cmake .. \
        -DGGML_CUDA=ON \
        -DGGML_BLAS=ON \
        -DGGML_BLAS_VENDOR=OpenBLAS \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
        -DCMAKE_C_COMPILER_LAUNCHER=ccache && \
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