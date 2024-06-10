#!/usr/bin/env python3
#
# Show bulk_match_* and bulk_unfiltered streams.
# Show their age, size and speed.
#
# Make sure you have NATS_URL, NATS_CA, NATS_USER, etc.. set in the env.
#
from collections import namedtuple
from datetime import datetime
from json import loads
from subprocess import CalledProcessError, check_output
from sys import stderr


StreamInfo = namedtuple('StreamInfo', 'description')

EXPECTED_STREAMS = {
    'bulk_match_aide': StreamInfo('AIDE changed files monitoring'),
    'bulk_match_audit': StreamInfo('Misc. auditd/pam logging'),
    'bulk_match_devinfra': StreamInfo('Git/CI/CD workflow'),
    'bulk_match_etcd': StreamInfo('etcd logs'),
    'bulk_match_execve': StreamInfo('Monitoring execve() calls'),
    'bulk_match_firewall': StreamInfo('Kernel iptables output'),
    'bulk_match_haproxy': StreamInfo('Haproxy requests/logs'),
    'bulk_match_hids': StreamInfo('Anti-virus (ClamAV) logs'),
    'bulk_match_k8s': StreamInfo('Kubernetes logs'),
    'bulk_match_k8s-audit': StreamInfo('Kubernetes audit logs'),
    'bulk_match_monitoring': StreamInfo('Gocollect/Zabbix logs'),
    'bulk_match_nginx': StreamInfo('nginx requests/logs'),
    'bulk_match_nids': StreamInfo('Suricata logs'),
    'bulk_match_ssh': StreamInfo('ssh logs (without pam noise)'),
    'bulk_match_systemd': StreamInfo('systemd daemon logs'),
    'bulk_match_unknown': StreamInfo('Logs not matched by something else'),
    'bulk_match_v12n': StreamInfo('containerd/docker logs'),
    'bulk_match_vault': StreamInfo('Vault logs'),
    'bulk_unfiltered': StreamInfo('Input'),
}


class Stream:
    @classmethod
    def build(cls, name, description):
        state = nats('stream', 'state', name)
        assert state['config']['discard'] == 'old', state

        max_bytes = state['config']['max_bytes']
        is_full = ((state['state']['bytes'] / max_bytes) > 0.9)
        bytes_gb = max_bytes / (1024 * 1024 * 1024)

        first_ts, first_ts_ns = cls.parse_tz(state['state']['first_ts'])
        last_ts, last_ts_ns = cls.parse_tz(state['state']['last_ts'])
        age = (last_ts - first_ts).total_seconds()

        msgs_k = state['state']['messages'] / 1000

        return cls(
            name, description, age / 3600, bytes_gb, is_full, msgs_k)

    @staticmethod
    def parse_tz(tzstr):
        assert tzstr.startswith('2') and tzstr.endswith('Z'), tzstr
        tzstr, nanosecs = tzstr.rsplit('.', 1)
        nanosecs = nanosecs[0:-1].ljust(9, '0')
        assert len(nanosecs) == 9, (tzstr, nanosecs)
        nanosecs = int(nanosecs)
        dt = datetime.strptime(tzstr, '%Y-%m-%dT%H:%M:%S')
        dt.replace(microsecond=(nanosecs // 1000))
        return dt, nanosecs

    def __init__(
            self, name, description, age_h, bytes_gb, is_full, msgs_k):
        self.name = name
        self.description = description
        self.age_h = age_h
        self.bytes_gb = bytes_gb
        self.is_full = is_full
        self.msgs_k = msgs_k


def nats(*args):
    try:
        output = check_output(('nats',) + args + ('--json',), shell=False)
    except CalledProcessError:
        raise
    output = output.decode('utf-8')
    data = loads(output)
    return data


def main():
    streams = []
    stream_names = nats('stream', 'ls')
    seen_unknown_stream = False

    for stream_name in stream_names:
        try:
            stream_info = EXPECTED_STREAMS[stream_name]
        except KeyError:
            if not seen_unknown_stream:
                print(
                    f'warning: Unknown stream {stream_name}; reporting once',
                    file=stderr)
                seen_unknown_stream = True
        else:
            stream = Stream.build(stream_name, *stream_info)

        streams.append(stream)

    fmth = (
        '{name:22s}  {age:>4s}  {bytes:>6s}  {msgs:>6s}  {speed:>7s}  {desc}')
    fmtd = (
        '{name:22s}  {age:3d}h  {bytes:5d}G{is_full} {msgs:5}k  '
        '{speed:4d}k/h  {desc}')
    print(fmth.format(
        name='NAME', age='AGE', bytes='BYTES', msgs='MSGS',
        speed='SPEED', desc='DESCRIPTION'))
    for stream in streams:
        print(fmtd.format(
            name=stream.name, age=int(stream.age_h),
            bytes=int(round(stream.bytes_gb)),
            is_full=(' ' if stream.is_full else '-'),
            msgs=int(round(stream.msgs_k)),
            speed=int(round(stream.msgs_k / stream.age_h)),
            desc=stream.description))


if __name__ == '__main__':
    main()
