"""factory_boy factories. Each module's tests append factories here as needed."""
from factory.alchemy import SQLAlchemyModelFactory

from tests.conftest import TestSessionLocal


class BaseFactory(SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = TestSessionLocal()
        sqlalchemy_session_persistence = "commit"
