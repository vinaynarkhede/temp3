"""TLS/SSL configuration and utilities."""

import ssl
import os
import ipaddress
from typing import Optional, Tuple
from pathlib import Path


class TLSConfig:
    """Configuration for TLS/SSL."""

    def __init__(
        self,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        verify_mode: ssl.VerifyMode = ssl.CERT_NONE
    ):
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        self.verify_mode = verify_mode

    def create_ssl_context(self, server_side: bool = True) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections."""
        if not self.cert_file or not self.key_file:
            return None

        if server_side:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        else:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        # Load certificate and key
        if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
            context.load_cert_chain(self.cert_file, self.key_file)

        # Load CA certificates if provided
        if self.ca_file and os.path.exists(self.ca_file):
            context.load_verify_locations(self.ca_file)

        context.verify_mode = self.verify_mode

        return context

    @classmethod
    def generate_self_signed_cert(
        cls,
        cert_file: str = "server.crt",
        key_file: str = "server.key",
        days: int = 365
    ) -> Tuple[str, str]:
        """Generate self-signed certificate for testing."""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime

            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"PyTunnel"),
                x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
            ])

            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(u"localhost"),
                    x509.DNSName(u"*.localhost"),
                    x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())

            # Write certificate to file
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            # Write private key to file
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            return cert_file, key_file

        except ImportError:
            raise ImportError(
                "cryptography package required for certificate generation. "
                "Install with: pip install cryptography"
            )


def get_ssl_context_for_server(
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None
) -> Optional[ssl.SSLContext]:
    """Get SSL context for server."""
    if not cert_file or not key_file:
        return None

    config = TLSConfig(cert_file=cert_file, key_file=key_file)
    return config.create_ssl_context(server_side=True)


def get_ssl_context_for_client(
    ca_file: Optional[str] = None,
    verify: bool = True
) -> Optional[ssl.SSLContext]:
    """Get SSL context for client."""
    verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    config = TLSConfig(ca_file=ca_file, verify_mode=verify_mode)
    return config.create_ssl_context(server_side=False)
