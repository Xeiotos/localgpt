# ---------- Build stage ----------
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 AS builder

RUN apt-get update && apt-get install -y \
    git build-essential cmake ninja-build mold pkg-config \
    libopenblas-dev \
 && rm -rf /var/lib/apt/lists/*

# Make CUDA stub driver visible during link (no driver in docker build)
ENV CUDA_STUBS=/usr/local/cuda/targets/x86_64-linux/lib/stubs
ENV LD_LIBRARY_PATH=${CUDA_STUBS}:${LD_LIBRARY_PATH}
RUN ln -sf ${CUDA_STUBS}/libcuda.so ${CUDA_STUBS}/libcuda.so.1

WORKDIR /app
RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp.git

# Set your GPU arch via build arg; RTX 3080 = 86
ARG CUDA_ARCHS=86

# Configure: minimal server, CUDA, BLAS, static libs, IPO, Ninja + mold
RUN cmake -S /app/llama.cpp -B /app/llama.cpp/build \
      -DGGML_CUDA=ON \
      -DGGML_BLAS=ON \
      -DGGML_BLAS_VENDOR=OpenBLAS \
      -DLLAMA_BUILD_COMMON=ON \
      -DLLAMA_BUILD_TOOLS=ON \
      -DLLAMA_BUILD_SERVER=ON \
      -DLLAMA_BUILD_EXAMPLES=OFF \
      -DLLAMA_BUILD_TESTS=OFF \
      -DLLAMA_CURL=OFF \
      -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON \
      -DCMAKE_POLICY_DEFAULT_CMP0069=NEW \
      -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHS} \
      -G Ninja \
      -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=mold -Wl,-rpath-link,${CUDA_STUBS}" \
      -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=mold"

# Build ONLY the server target
RUN cmake --build /app/llama.cpp/build --target llama-server -j"$(nproc)"

# ---------- Runtime stage ----------
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y \
    libgomp1 libopenblas-base \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/llama.cpp/build/bin/llama-server /app/llama-server

EXPOSE 8502
ENTRYPOINT ["./llama-server"]
