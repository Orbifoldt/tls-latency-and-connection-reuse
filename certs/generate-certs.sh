#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

rm -rf root intermediate leaf ocsp
mkdir -p root intermediate leaf ocsp
chmod 700 root intermediate leaf ocsp

# Root CA configuration
cat > root/root.cnf <<'EOF'
[ req ]
distinguished_name = dn
x509_extensions = root_ca
prompt = no

[ dn ]
CN = My Root CA

[ root_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:1
keyUsage = critical, keyCertSign, cRLSign
EOF

# Intermediate CA configuration
cat > intermediate/intermediate.cnf <<'EOF'
[ req ]
distinguished_name = dn
prompt = no

[ dn ]
CN = My Intermediate CA

[ intermediate_ca ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = critical, CA:true, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
authorityInfoAccess = OCSP;URI:http://localhost:8001/ocsp
EOF

# Leaf/server certificate configuration
cat > leaf/leaf.cnf <<'EOF'
[ req ]
distinguished_name = dn
prompt = no

[ dn ]
CN = localhost

[ server_cert ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = critical, CA:false
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @san
authorityInfoAccess = OCSP;URI:http://localhost:8001/ocsp

[ san ]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Root CA
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out root/root.key.pem
openssl req -x509 -new -sha256 -days 3650 \
  -key root/root.key.pem -out root/root.cert.pem -config root/root.cnf

# Intermediate CA signed by root
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out intermediate/intermediate.key.pem
openssl req -new -sha256 -key intermediate/intermediate.key.pem \
  -out intermediate/intermediate.csr.pem -config intermediate/intermediate.cnf
openssl x509 -req -sha256 -days 1825 \
  -in intermediate/intermediate.csr.pem \
  -CA root/root.cert.pem -CAkey root/root.key.pem -CAcreateserial \
  -out intermediate/intermediate.cert.pem \
  -extfile intermediate/intermediate.cnf -extensions intermediate_ca

# Leaf/server certificate signed by intermediate
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out leaf/localhost.key.pem
openssl req -new -sha256 -key leaf/localhost.key.pem \
  -out leaf/localhost.csr.pem -config leaf/leaf.cnf
openssl x509 -req -sha256 -days 825 \
  -in leaf/localhost.csr.pem \
  -CA intermediate/intermediate.cert.pem -CAkey intermediate/intermediate.key.pem \
  -CAcreateserial -out leaf/localhost.cert.pem \
  -extfile leaf/leaf.cnf -extensions server_cert

cat intermediate/intermediate.cert.pem root/root.cert.pem > leaf/chain.cert.pem
cat leaf/localhost.cert.pem intermediate/intermediate.cert.pem > leaf/fullchain.cert.pem

# Keep a small inspection artifact for the certificate's OCSP identifiers.
openssl x509 -in leaf/localhost.cert.pem -ocspid -noout > ocsp/leaf-ocspid.txt

chmod 600 root/root.key.pem intermediate/intermediate.key.pem leaf/localhost.key.pem
rm -f root/root.cert.srl intermediate/intermediate.cert.srl

echo "Generated local PKI under $ROOT_DIR"
echo "Server key:       leaf/localhost.key.pem"
echo "Server fullchain: leaf/fullchain.cert.pem"
echo "Trust root:       root/root.cert.pem"
echo "OCSP URL:         http://localhost:8001/ocsp"
