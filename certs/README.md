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
- `leaf_revoked_crl/` => a second localhost leaf that is revoked in the generated CRL.
- `ca_server/intermediate.crl.pem` => CRL signed by the intermediate CA.
- `serials.txt` => serial numbers for the root, intermediate, and both leaf certificates.


The leaf contains this OCSP url:
```
http://localhost:6080/ocsp
```

The leaf also advertises this CRL Distribution Point, serving `certs/ca_server/intermediate.crl.pem` there:

```text
http://localhost:6080/crl/intermediate.crl.pem
```

NB: obviously, don't use these certs in prod...
