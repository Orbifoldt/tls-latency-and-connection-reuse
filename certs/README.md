This will generate all the certificates from scratch, see [README.md](../README.md) for details.

```sh
./certs/generate-certs.sh
```

Generated files:

- `root/root.cert.pem` => trust this certificate in the client (the truststore)
- `intermediate/intermediate.cert.pem` => signed by the root.
- `leaf/localhost.cert.pem` => server certificate for `localhost`, `127.0.0.1`, and `::1`.
- `leaf/localhost.key.pem` => server private key.
- `leaf/fullchain.cert.pem` => leaf plus intermediate, for the TLS server.
- `leaf/chain.cert.pem` => intermediate plus root, for inspection/testing.


The leaf contains this OCSP url:
```
http://localhost:8001/ocsp
```

NB: obviously, don't use these certs in prod...