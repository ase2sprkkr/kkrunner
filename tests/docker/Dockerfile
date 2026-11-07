FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        munge \
        libgfortran5 \
        liblapack3 \
        libopenblas0-pthread \
        openssh-server \
        python3 \
        python3-pip \
        python3-venv \
        slurm-wlm \
        tini \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv "$VIRTUAL_ENV" \
    && pip install "psij-python==0.9.11" platformdirs pytest setuptools wheel

COPY tests/docker/slurm.conf /etc/slurm/slurm.conf
COPY tests/docker/cgroup.conf /etc/slurm/cgroup.conf
COPY tests/docker/entrypoint.sh /usr/local/bin/kkrunner-test-entrypoint

RUN useradd -m -s /bin/bash tester \
    && chmod 0755 /usr/local/bin/kkrunner-test-entrypoint \
    && mkdir -p \
        /var/spool/slurmctld \
        /var/spool/slurmd \
        /var/log/slurm \
        /run/munge \
        /run/sshd \
        /var/lib/munge \
        /var/log/munge \
        /root/.config/kkrunner \
        /home/tester/.config/kkrunner \
        /home/tester/.ssh \
        /workspace \
    && chown -R tester:tester /home/tester/.config /home/tester/.ssh \
    && chmod 0700 /home/tester/.ssh \
    && printf '%s\n' \
        'PasswordAuthentication no' \
        'PermitRootLogin no' \
        'PubkeyAuthentication yes' \
        > /etc/ssh/sshd_config.d/kkrunner-test.conf \
    && chown -R slurm:slurm /var/spool/slurmctld /var/log/slurm \
    && chown -R munge:munge /run/munge /var/lib/munge /var/log/munge

WORKDIR /workspace
EXPOSE 22
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/kkrunner-test-entrypoint"]
CMD ["sleep", "infinity"]

COPY pyproject.toml README.md LICENCE /workspace/kkrunner/
COPY src /workspace/kkrunner/src
COPY tests/docker/psij_slurm_test_in_docker.py /workspace/kkrunner/tests/docker/
RUN pip install --no-build-isolation --no-deps /workspace/kkrunner
