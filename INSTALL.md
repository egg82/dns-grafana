## Notes
This guide was designed for a fresh install of [Ubuntu server 20.04](https://ubuntu.com/download/server)

### Install Python/deps
```Bash
sudo apt install python3 python3-pip python3-dev
python3 -m pip install tailer
python3 -m pip install python-dateutil
```

### Install Unbound
Install unbound
```Bash
sudo apt install unbound
```

Create the file `/etc/unbound/unbound.conf.d/coredns.conf` and add the following, adjusting for your own DoT or forwarding preferences:
```Conf
server:
    # If no logfile is specified, syslog is used
    # logfile: "/var/log/unbound/unbound.log"
    verbosity: 2

    port: 5353
    do-ip4: yes
    do-udp: yes
    do-tcp: yes

    # May be set to yes if you have IPv6 connectivity
    do-ip6: yes

    # Unjail/log
    chroot: ""
    log-time-ascii: yes
    logfile: "/var/log/unbound.log"

    # Use this only when you downloaded the list of primary root servers!
    root-hints: "/var/lib/unbound/root.hints"

    # Use DNS-over-TLS with the specified bundle
    tls-cert-bundle: /etc/ssl/certs/ca-certificates.crt

    # Trust glue only if it is within the server's authority
    harden-glue: yes

    # Require DNSSEC data for trust-anchored zones, if such data is absent, the zone becomes BOGUS
    harden-dnssec-stripped: yes

    # Don't use Capitalization randomization as it known to cause DNSSEC issues sometimes
    # see https://discourse.pi-hole.net/t/unbound-stubby-or-dnscrypt-proxy/9378 for further details
    use-caps-for-id: no

    # Reduce EDNS reassembly buffer size.
    # Suggested by the unbound man page to reduce fragmentation reassembly problems
    edns-buffer-size: 1472

    # Perform prefetching of close to expired message cache entries
    # This only applies to domains that have been frequently queried
    prefetch: yes

    # One thread should be sufficient, can be increased on beefy machines. In reality for most users running on small networks or on a single machine, it should be unnecessary to seek performance enhancement by increasing num-threads above 1.
    num-threads: 2

    # Ensure kernel buffer is large enough to not lose messages in traffic spikes
    so-rcvbuf: 1m

    # Ensure privacy of local IP ranges
    private-address: 192.168.0.0/16
    private-address: 169.254.0.0/16
    private-address: 172.16.0.0/12
    private-address: 10.0.0.0/8
    private-address: fd00::/8
    private-address: fe80::/10

forward-zone:
    name: "."
    forward-tls-upstream: yes
    # Google
    forward-addr: 8.8.8.8@853#dns.google
    forward-addr: 8.8.4.4@853#dns.google
    #forward-addr: 2001:4860:4860::8888@853#dns.google
    #forward-addr: 2001:4860:4860::8844@853#dns.google
    # Cloudflare
    #forward-addr: 2606:4700:4700::1111@853#cloudflare-dns.com
    forward-addr: 1.1.1.1@853#cloudflare-dns.com
    #forward-addr: 2606:4700:4700::1001@853#cloudflare-dns.com
    forward-addr: 1.0.0.1@853#cloudflare-dns.com
```

Create the log file:
```Bash
sudo touch /var/log/unbound.log
sudo chown unbound:unbound /var/log/unbound.log
```

Edit the file `/etc/sysctl.conf` and add (or edit) the following line:
```Conf
net.core.rmem_max=8388608
```

Reload sysctl
```Bash
sudo sysctl -p
```

Download the root hints for DNSSEC
```Bash
sudo wget -O /root/root.hints https://www.internic.net/domain/named.root && sudo mv /root/root.hints /var/lib/unbound/ && sudo service unbound restart
```

Edit the root crontab
```Bash
sudo crontab -e
```

Add the following to the root's crontab
```
0 0 * * 0 wget -O /root/root.hints https://www.internic.net/domain/named.root && mv /root/root.hints /var/lib/unbound/ && service unbound restart
```

### Install CoreDNS
Install CoreDNS
```Bash
core_version=1.7.0
sudo useradd -M -s /bin/false coredns
cd ~
wget https://github.com/coredns/coredns/releases/download/v$core_version/coredns_"$core_version"_linux_amd64.tgz
tar -xvf coredns_"$core_version"_linux_amd64.tgz
sudo mv coredns /usr/local/bin
sudo chown coredns:coredns /usr/local/bin/coredns
sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/local/bin/coredns
```

Create the file `/etc/systemd/system/coredns.service` and add the following:
```ini
[Unit]
Description=CoreDNS Server
After=network.target

[Service]
Type=simple
Restart=on-failure
User=coredns
Group=coredns
StandardOutput=syslog
StandardError=syslog
ExecStart=/usr/local/bin/coredns -conf /etc/coredns/Corefile
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

Reload systemctl
```Bash
sudo systemctl daemon-reload
```

Create the config directory
```Bash
sudo mkdir -p /etc/coredns
```

Create the file `/etc/coredns/Corefile` and add the following, adjusting for your subnet:
```
.:53 {
        forward . 127.0.0.1:5353
        file /etc/coredns/db.internal.net       internal.net
        file /etc/coredns/db.192.168            192.168.in-addr.arpa
        nsid Internal home network
        dnssec

        cache
        cancel
        bufsize 1232

        log
        errors
}
```

Create the file `/etc/coredns/db.internal.net` and add the following, adjusting for your subnet and records:
```
$TTL    604800
@       IN      SOA     dns.internal.net.     admin.internal.net. (
        3               ; Serial
        604800          ; Refresh
        86400           ; Retry
        2419200         ; Expire
        604800          ; Negative cache TTL
)

; NS records
@       IN      NS      dns

; A records
ctl.internal.net.     IN      A       192.168.0.2
nas.internal.net.     IN      A       192.168.0.5
dns.internal.net.     IN      CNAME   lab.internal.net.
plex.internal.net.    IN      CNAME   lab.internal.net.
homelab.internal.net. IN      CNAME   lab.internal.net.
lab.internal.net.     IN      A       192.168.0.6
```

Create the file `/etc/coredns/db.192.168` and add the following, adjusting for your subnet and records:
```
$TTL    604800
@       IN      SOA     dns.internal.net.     admin.internal.net. (
        3               ; Serial
        604800          ; Refresh
        86400           ; Retry
        2419200         ; Expire
        604800          ; Negative cache TTL
)

; NS records
@       IN      NS      dns

; PTR records
2.0   IN      PTR     ctl.internal.net. ; 192.168.   0.2
5.0   IN      PTR     nas.internal.net. ; 192.168.   0.5
6.0   IN      PTR     lab.internal.net. ; 192.168.   0.6
```

chown/chmod the config directory and files
```Bash
sudo chown -R coredns:coredns /etc/coredns
sudo chmod -R 0664 /etc/coredns
sudo chmod 0775 /etc/coredns
```

Create the log file for CoreDNS
```Bash
sudo touch /var/log/coredns.log
sudo chown syslog:adm /var/log/coredns.log
```

Create `/etc/rsyslog.d/coredns.conf` and add the following:
```Conf
if $programname == 'coredns' then /var/log/coredns.log
& stop
```

Resatrt syslog
```Bash
sudo systemctl restart syslog
```

### Disable resolved
```Bash
sudo systemctl disable systemd-resolved
sudo systemctl stop systemd-resolved
```

### Enable CoreDNS/Unbound
```Bash
sudo systemctl enable unbound
sudo systemctl start unbound
sudo systemctl enable coredns
sudo systemctl start coredns
```

### CoreDNS Elasticsearch
```Bash
curl -X DELETE "http://localhost:9200/coredns?pretty"
curl -X PUT "http://localhost:9200/coredns?pretty"
curl -X PUT "http://localhost:9200/coredns/_mapping?pretty" -H 'Content-Type: application/json' -d'
{
  "properties": {
    "level": {
      "type": "keyword",
      "index": true
    },
    "remote": {
      "type": "keyword",
      "index": true
    },
    "type": {
      "type": "keyword",
      "index": true
    },
    "name": {
      "type": "keyword",
      "index": true
    },
    "dnssec": {
      "type": "boolean",
      "index": true
    },
    "code": {
      "type": "keyword",
      "index": true
    },
    "duration": {
      "type": "double",
      "index": true
    },
    "date": {
      "type": "date",
      "index": true,
      "format": "MMM d, yyyy '\''at'\'' hh:mm:ssa"
    }
  }
}
'
curl -X GET "http://localhost:9200/coredns/_search?pretty"
```

### Unbound Elasticsearch
```Bash
curl -X DELETE "http://localhost:9200/unbound?pretty"
curl -X PUT "http://localhost:9200/unbound?pretty"
curl -X PUT "http://localhost:9200/unbound/_mapping?pretty" -H 'Content-Type: application/json' -d'
{
  "properties": {
    "level": {
      "type": "keyword",
      "index": true
    },
    "server": {
      "type": "keyword",
      "index": true,
      "null_value": ""
    },
    "type": {
      "type": "keyword",
      "index": true
    },
    "name": {
      "type": "keyword",
      "index": true
    },
    "dnssec": {
      "type": "boolean",
      "index": true
    },
    "date": {
      "type": "date",
      "index": true,
      "format": "MMM d, yyyy '\''at'\'' hh:mm:ssa"
    }
  }
}
'
curl -X GET "http://localhost:9200/unbound/_search?pretty"
```
