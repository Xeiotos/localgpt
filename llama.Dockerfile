# ---------- Build stage ----------
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    git build-essential cmake ccache pkg-config wget \
    libopenblas-dev \
  && rm -rf /var/lib/apt/lists/*

# Make the CUDA stub driver visible to the linker during build
ENV CUDA_STUBS=/usr/local/cuda/targets/x86_64-linux/lib/stubs
ENV LD_LIBRARY_PATH=${CUDA_STUBS}:${LD_LIBRARY_PATH}
# Some linkers look specifically for .so.1 – provide it
RUN ln -sf ${CUDA_STUBS}/libcuda.so ${CUDA_STUBS}/libcuda.so.1

WORKDIR /app

RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -S . -B build \
      -DLLAMA_CURL=OFF \
      -DGGML_CUDA=ON \
      -DGGML_BLAS=ON \
      -DGGML_BLAS_VENDOR=OpenBLAS \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
      -DCMAKE_C_COMPILER_LAUNCHER=ccache \
      -DLLAMA_BUILD_TOOLS=OFF \
      -DLLAMA_BUILD_TESTS=OFF \
      -DLLAMA_BUILD_EXAMPLES=OFF \
      -DLLAMA_BUILD_SERVER=ON \
      -DCMAKE_EXE_LINKER_FLAGS="-Wl,-rpath-link,${CUDA_STUBS}" \
    && cmake --build build --config Release -j"$(nproc)"

# ---------- Runtime stage ----------
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    libgomp1 libopenblas-base \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy server + its shared libs
COPY --from=builder /app/llama.cpp/build/bin/llama-server /app/llama-server
COPY --from=builder /app/llama.cpp/build/bin/libggml*.so /usr/local/lib/
COPY --from=builder /app/llama.cpp/build/bin/libllama*.so /usr/local/lib/
RUN ldconfig

EXPOSE 8502
ENTRYPOINT ["./llama-server"]