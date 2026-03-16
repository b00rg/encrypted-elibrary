from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from crypto import generate_aes_key

RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537
EXPIRY = 365

def generate_rsa_keypair() -> tuple:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    return private_key, private_key.public_key()

def serialize_private_key(private_key, password: bytes) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password)
    )

def deserialize_private_key(pem_data: bytes, password: bytes):
    return serialization.load_pem_private_key(
        pem_data, 
        password=password
    )

def serialize_public_key(public_key) -> bytes:
    return public_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def deserialize_public_key(pem_data: bytes):
    return serialization.load_pem_public_key(
        pem_data
    )

def generate_certificate(username: str, private_key, public_key) -> x509.Certificate:
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, username),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Secure Pinterest Group"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .sign(private_key, hashes.SHA256())
    )

    return cert

def serialize_certificate(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)

def deserialize_certificate(pem_data: bytes) -> x509.Certificate:
    return x509.load_pem_x509_certificate(pem_data)


def get_username_from_cert(cert: x509.Certificate) -> str:
    return cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

def wrap_group_key(aes_key: bytes, recipient_public_key) -> bytes:
    return recipient_public_key.encrypt(
        aes_key,

        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

def unwrap_group_key(wrapped_key: bytes, private_key) -> bytes:
    try:

        aes_key = private_key.decrypt(
            wrapped_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return aes_key
    
    except Exception as e:
        raise ValueError(f"Failed to unwrap group key: {e}")

def create_group(admin_public_key) -> tuple:
    aes_key = generate_aes_key()
    wrapped_group_key = wrap_group_key(aes_key=aes_key,recipient_public_key=admin_public_key)
    return aes_key, wrapped_group_key

def add_member(aes_key: bytes, new_member_cert_pem: bytes) -> bytes:
    cert = deserialize_certificate(pem_data=new_member_cert_pem)
    new_member_public_key = cert.public_key()
    return wrap_group_key(aes_key, new_member_public_key)

def remove_member(remaining_member_certs_pem: list) -> tuple:
    aes_key = generate_aes_key()
    new_group = {}

    for member_cert_pem in remaining_member_certs_pem:
        cert = deserialize_certificate(pem_data=member_cert_pem)
        new_member_public_key = cert.public_key()
        username = get_username_from_cert(cert)
        new_group[username] = new_member_public_key
        
    return aes_key, new_group