# tls-latency-and-connection-reuse
> This started with the idea that online checks during a SSL handshake can be a cause of latency, and that connection reuse can be a way to avoid that latency.
> However, it turns out that most (if not all) HTTP clients in python do not do any of these checks. 

## Background info
HTTPS is an HTTP connection that is secured by SSL / TLS. It is built on top of X.509 certificates, which are issued by a certificate authority (CA). The CA signs the certificate, and the client can verify the signature using the CA's public key. (We'll not go into too much details on this kind of Public Key Infrastructure (PKI) here). When a client connects to a server over HTTPS, it performs a TLS handshake, during which the client verifies the server's certificate: it checks the certificate's validity period, its signature.

Besides these (offline) checks, certificate authorities should have a way of revoking someone's certificate (if it's compromised, or for other reasons). This (basically by definition) requires an online check. There's several mechanisms for this:
- CRL (Certificate Revocation List): the CA publishes a list of revoked certificates, and the client can download this list and just check if the server's certificate is on it.
- OCSP (Online Certificate Status Protocol): the client can query an "OCSP responder", which is a server (run by the CA) to check if the certificate is revoked. The responder answers with a (signed) response: 
  - good: the certificate is valid
  - revoked: the certificate is revoked
  - unknown: the responder doesn't know about this certificate (e.g. it was not issued by this CA)
- OCSP Stapling: when the server provides its certificate to the client, it can also provide a recent OCSP response (signed by the CA) stating if the certificate is valid or revoke. The difference with normal OCSP is that the client doesn't make the request to the OCSP responder, but it's the server itself. Because the OCSP response was signed, this is not a security issue. Moreover, OCSP stapling is done in the TLS handshake, which generally falls outside the scope of an HTTP client library like httpx. 


Problems with this:
- CRL: As downloading the CRL everytime can be slow, it's usually cached. But these list may be very large, so generally this is somewhat inefficient.
- OCSP: This requires an online request, which can be slow and can fail (e.g. if the OCSP responder is down). If there's no response, it's the question if you should fail open (insecure) or fail closed (adds a new dependency to your system). Also, privacy wise, this tells the OCSP responder which sites you are visiting.


As far as I can tell, browsers generally implement these methods. But in programming languages, the usual http clients do not implement these checks. For example, in python, the `httpx` library does only support CRL checking (via the Python SSLContext itself), but this requires you to manually download the CRL, and this is not enabled by default. The JVM seems to support most of this, but again these check are not enabled by default (so who actually checks it then?).

## Application components
Layout of this demo: 

TODO: diagram

### Server
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



### Client
A simple python FastAPI app, that has several endpoints which trigger it to call our Server:
- `/crl`

```sh
make client-run
```

Then call the endpoints:

#### CRL check for valid certificate:
```sh
curl http://localhost:7000/crl?revoked=False --silent | jq
```
```json
{
  "status_code": 200,
  "body_content": "{\"message\":\"Hello, greetings from the server!\"}",
}
```

#### CRL check for revoked certificate:
```sh
curl http://localhost:7000/crl?revoked=True --silent | jq
```
```json
{
  "error": "Could not connect to server: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate revoked (_ssl.c:1032)"
}
```

#### CRL check with auto-discovered CRL URL for revoked certificate:
This dynamically gets CRL URL from the presented certificate (instead of it being hardcoded)
```sh
curl http://localhost:7000/crl-auto?revoked=True --silent | jq
```
```json
{
  "error": "Could not connect to server: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate revoked (_ssl.c:1032)"
}
```

#### TODO 
OCSP and OCSP stapling...

#### Default httpx (no checks):
These both will just return 200 responses:
```sh
curl http://localhost:7000/default?revoked=False
```
```sh
curl http://localhost:7000/default?revoked=True
```

### CA Server
A FastAPI server that is: 
- offers a Certificate Revocation List (CRL) for the intermediate CA at `http://localhost:6080/crl/intermediate.crl.pem`. This is a signed file containing the serial numbers of revoked certificates.
- TODO: a proxy for a simple openssl OCSP responder. It controls the responder via a file-based set of issued certs and their revocation status. Also, we can control its latency.

Run it by:
```sh
make ca-server-run
```
