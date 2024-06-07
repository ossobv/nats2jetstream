#FROM rust:1.75 AS builder
FROM ghcr.io/rust-cross/rust-musl-cross:x86_64-musl AS builder

USER root
RUN mkdir -p /src/natsomatch/target /usr/local/cargo && \
    chown nobody: /src/natsomatch/target /usr/local/cargo

ENV CARGO_HOME=/usr/local/cargo

USER nobody
WORKDIR /src/natsomatch

RUN cargo --version
RUN cargo install cargo-auditable cargo-audit

# Copy prerequisites for cargo update/fetch
COPY Cargo.lock Cargo.toml /src/natsomatch/
COPY benches /src/natsomatch/benches
COPY lib /src/natsomatch/lib
COPY src/lib.rs /src/natsomatch/src/lib.rs

# Update/fetch
RUN cargo update --dry-run --locked
RUN cargo fetch --locked --verbose

# Waiting on https://github.com/rust-lang/cargo/issues/2644
# Then we could do a pre-build before adding most of our sources.
#RUN GIT_VERSION=irrelevant cargo auditable build --locked --features=version-from-env \
#      --release --target x86_64-unknown-linux-musl

# Copy the rest of the source
COPY . /src/natsomatch
#RUN cargo update --dry-run --locked
#RUN cargo fetch --locked --verbose
#RUN rustup target add x86_64-unknown-linux-musl

ARG GIT_VERSION
#RUN cargo build --features=version-from-env
#RUN cargo test --features=version-from-env
#RUN cargo bench --features=version-from-env
RUN cargo auditable build --locked --features=version-from-env \
      --release --target x86_64-unknown-linux-musl
RUN test "$(echo $(ldd target/x86_64-unknown-linux-musl/release/natsomatch))" = "statically linked"

FROM scratch
COPY --from=builder /src/natsomatch/target/x86_64-unknown-linux-musl/release/natsomatch /natsomatch
