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