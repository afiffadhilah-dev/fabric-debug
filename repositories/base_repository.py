"""
Base repository with common CRUD operations.

Provides a foundation for all domain-specific repositories.
"""

from typing import TypeVar, Generic, Optional, List, Type, Any
from sqlmodel import Session, select, SQLModel
from uuid import UUID

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Generic base repository with common CRUD operations.
    
    Type Parameters:
        T: SQLModel entity type
    """

    def __init__(self, db_session: Session, model_class: Type[T]):
        """
        Initialize repository.
        
        Args:
            db_session: SQLModel database session
            model_class: The SQLModel class this repository manages
        """
        self.db = db_session
        self.model_class = model_class

    def get_by_id(self, id: Any) -> Optional[T]:
        """
        Get entity by ID.
        
        Args:
            id: Primary key (UUID or str)
            
        Returns:
            Entity if found, None otherwise
        """
        return self.db.get(self.model_class, id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """
        Get all entities with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of records to skip
            
        Returns:
            List of entities
        """
        statement = select(self.model_class).offset(offset).limit(limit)
        return list(self.db.exec(statement).all())

    def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: Entity to create
            
        Returns:
            Created entity with ID
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: Entity with updated values
            
        Returns:
            Updated entity
        """
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> bool:
        """
        Delete an entity.
        
        Args:
            entity: Entity to delete
            
        Returns:
            True if deleted
        """
        self.db.delete(entity)
        self.db.commit()
        return True

    def delete_by_id(self, id: Any) -> bool:
        """
        Delete entity by ID.
        
        Args:
            id: Primary key
            
        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if entity:
            return self.delete(entity)
        return False

    def exists(self, id: Any) -> bool:
        """
        Check if entity exists.
        
        Args:
            id: Primary key
            
        Returns:
            True if exists
        """
        return self.get_by_id(id) is not None
