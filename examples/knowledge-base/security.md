# Security and API keys (sample knowledge base)

API keys are created under Settings > Developer > API keys. Each key is shown once; store it in a secrets manager.

Rotating a key: create the new key, deploy it, confirm traffic on the new key in the usage graph, then revoke the
old key. Revoked keys stop working within 60 seconds.

Data is encrypted at rest with AES-256 and in transit with TLS 1.2 or newer. Customer data is never used to train
models. Security issues can be reported to the security contact listed in SECURITY.md.
