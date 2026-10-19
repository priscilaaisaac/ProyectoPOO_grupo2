"""
Email configurations.
"""

import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


class AbsEmailServerConfig(ABC):
    """Abstract base class defining required properties for an email server configuration."""

    @property
    @abstractmethod
    def mail_server(self) -> str:
        pass

    @property
    @abstractmethod
    def mail_port(self) -> int:
        pass

    @property
    @abstractmethod
    def mail_username(self) -> str:
        pass

    @property
    @abstractmethod
    def mail_password(self) -> str:
        pass

    @property
    @abstractmethod
    def name_sender(self) -> str:
        pass

    @property
    @abstractmethod
    def mail_sender_address(self) -> str:
        pass

    @property
    @abstractmethod
    def mail_use_tls(self) -> bool:
        pass


class EmailEnvConfig(AbsEmailServerConfig):
    """Email server configuration that loads values from environment variables."""

    def __init__(self):
        required_vars = [
            'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME',
            'MAIL_PASSWORD', 'MAIL_SENDER_ADDRESS', 'NAME_SENDER'
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f'Missing required environment variables for Email config: {", ".join(missing)}')

    @property
    def mail_server(self) -> str:
        return os.getenv('MAIL_SERVER')

    @property
    def mail_port(self) -> int:
        return int(os.getenv('MAIL_PORT', '587'))

    @property
    def mail_username(self) -> str:
        return os.getenv('MAIL_USERNAME')

    @property
    def mail_password(self) -> str:
        return os.getenv('MAIL_PASSWORD')

    @property
    def name_sender(self) -> str:
        return os.getenv('NAME_SENDER')

    @property
    def mail_sender_address(self) -> str:
        return os.getenv('MAIL_SENDER_ADDRESS')

    @property
    def mail_use_tls(self) -> bool:
        return os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
