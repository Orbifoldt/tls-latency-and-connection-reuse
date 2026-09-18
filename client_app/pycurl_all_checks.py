
# TODO: high level plan:
# import pycurl
# from io import BytesIO
#
# buffer = BytesIO()
#
# curl = pycurl.Curl()
# curl.setopt(pycurl.URL, "URL_HERE...")
# curl.setopt(pycurl.WRITEDATA, buffer)
# curl.setopt(pycurl.SSL_VERIFYPEER, 1)
# curl.setopt(pycurl.SSL_VERIFYHOST, 2)
#
# # CRL checking:
# curl.setopt(pycurl.CRLFILE, "/path/to/crl.crl")
#
# # OCSP stapling checking:
# curl.setopt(pycurl.SSL_VERIFYSTATUS, 1)
#
# curl.perform()
# curl.close()
#
# # Read data
# print(buffer.getvalue())
