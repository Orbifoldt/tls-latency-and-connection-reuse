#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

rm -rf root intermediate leaf ca_server serials.txt
mkdir -p root intermediate/newcerts leaf ca_server
chmod 700 root intermediate leaf ca_server

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
authorityInfoAccess = OCSP;URI:http://localhost:6080/ocsp
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
authorityInfoAccess = OCSP;URI:http://localhost:6080/ocsp
crlDistributionPoints = URI:http://localhost:6080/crl/intermediate.crl.pem

[ san ]
DNS.1 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

cat > intermediate/ca.cnf <<EOF
[ ca ]
default_ca = CA_default

[ CA_default ]
dir = $ROOT_DIR/intermediate
database = \$dir/index.txt
new_certs_dir = \$dir/newcerts
certificate = \$dir/intermediate.cert.pem
private_key = \$dir/intermediate.key.pem
serial = \$dir/serial
crlnumber = \$dir/crlnumber
default_crl_days = 30
default_days = 825
default_md = sha256
policy = policy_loose
email_in_dn = no
unique_subject = no

[ policy_loose ]
commonName = supplied

[ server_cert ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = critical, CA:false
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @san
authorityInfoAccess = OCSP;URI:http://localhost:6080/ocsp
crlDistributionPoints = URI:http://localhost:6080/crl/intermediate.crl.pem

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

# Initialize the intermediate CA database used for leaf certificates and CRLs.
: > intermediate/index.txt
printf '1000\n' > intermediate/serial
printf '1000\n' > intermediate/crlnumber

generate_leaf() {
  local output_dir="$1"
  local certificate_name="$2"

  mkdir -p "$output_dir"
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
    -out "$output_dir/$certificate_name.key.pem"
  openssl req -new -sha256 -key "$output_dir/$certificate_name.key.pem" \
    -out "$output_dir/$certificate_name.csr.pem" -config leaf/leaf.cnf
  openssl ca -batch -config intermediate/ca.cnf \
    -in "$output_dir/$certificate_name.csr.pem" \
    -out "$output_dir/$certificate_name.cert.pem" \
    -extensions server_cert

  cat intermediate/intermediate.cert.pem root/root.cert.pem \
    > "$output_dir/chain.cert.pem"
  cat "$output_dir/$certificate_name.cert.pem" intermediate/intermediate.cert.pem \
    > "$output_dir/fullchain.cert.pem"
}

# Normal leaf/server certificate.
generate_leaf leaf localhost

# Demo leaf that is immediately revoked in the intermediate CA database.
generate_leaf leaf_revoked_crl localhost-revoked-crl
openssl ca -batch -config intermediate/ca.cnf \
  -revoke leaf_revoked_crl/localhost-revoked-crl.cert.pem

# Generate the current CRL. The ca_server should serve this file at /crl/.
openssl ca -batch -config intermediate/ca.cnf -gencrl \
  -out ca_server/intermediate.crl.pem

# Keep certificate serials in one human-readable, script-friendly manifest.
{
  printf 'certificate\tserial\n'
  printf 'root\t%s\n' "$(openssl x509 -in root/root.cert.pem -noout -serial | cut -d= -f2)"
  printf 'intermediate\t%s\n' "$(openssl x509 -in intermediate/intermediate.cert.pem -noout -serial | cut -d= -f2)"
  printf 'leaf\t%s\n' "$(openssl x509 -in leaf/localhost.cert.pem -noout -serial | cut -d= -f2)"
  printf 'leaf_revoked_crl\t%s\n' "$(openssl x509 -in leaf_revoked_crl/localhost-revoked-crl.cert.pem -noout -serial | cut -d= -f2)"
} > serials.txt

# Keep the OCSP identifiers available to the ca_server implementation.
openssl x509 -in leaf/localhost.cert.pem -ocspid -noout > ca_server/leaf-ocspid.txt
openssl x509 -in leaf_revoked_crl/localhost-revoked-crl.cert.pem -ocspid -noout \
  > ca_server/leaf-revoked-crl-ocspid.txt

chmod 600 root/root.key.pem intermediate/intermediate.key.pem \
  leaf/*.key.pem leaf_revoked_crl/*.key.pem
rm -f root/root.cert.srl

echo "Generated local PKI under $ROOT_DIR"
echo "Server key:       leaf/localhost.key.pem"
echo "Server fullchain: leaf/fullchain.cert.pem"
echo "Trust root:       root/root.cert.pem"
echo "OCSP URL:         http://localhost:6080/ocsp"
echo "CRL URL:          http://localhost:6080/crl/intermediate.crl.pem"
echo "Serial manifest:  serials.txt"
