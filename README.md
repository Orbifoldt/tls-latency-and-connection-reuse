# tls-latency-and-connection-reuse

TODO: diagram

## Server
A simple FastAPI server. Nginx redirects HTTP on port 8080 to HTTPS on port 8443, terminates TLS there, and proxies to Uvicorn on the container-only port 9080.

Build and run the server:
```sh
make server-run
```

Test the HTTP to HTTPS upgrade/redirect via:
```sh
curl -I http://localhost:8080/
```

We should trust `certs/root/root.cert.pem`, so we can test simply with:
```sh
curl --cacert certs/root/root.cert.pem https://localhost:8443/
```

NB: this excludes OCSP verification, which curl seemingly doesn't do?



## Client
