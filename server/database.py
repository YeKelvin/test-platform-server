#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File    : database.py
# @Time    : 2019/11/7 10:57
# @Author  : Kelvin.Ye

"""
Database module, including the SQLAlchemy database object and DB-related utilities.
"""

from server.extensions import db
from server.utils.log_util import get_logger

log = get_logger(__name__)


class CRUDMixin:
    """Mixin that adds convenience methods for CRUD (create, read, update, delete) operations.
    """

    @classmethod
    def create(cls, commit=True, **kwargs):
        """Create a new record and save it the database.
        """
        instance = cls(**kwargs)
        return instance.save(commit)

    @classmethod
    def query_by(cls, DEL_STATE=0, **kwargs):
        return cls.query.filter_by(DEL_STATE=DEL_STATE, **kwargs)

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record.
        """
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and self.save() or self

    def update_with_time(self, commit=True, **kwargs):
        return self.update(commit=commit, UPDATED_TIME=getattr(self, 'UPDATED_TIME'), **kwargs)

    def save(self, commit=True):
        """Save the record.
        """
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        """Remove the record from the database.
        """
        return self.update(commit=commit, DEL_STATE=1)


class DBModel(CRUDMixin, db.Model):
    """Base model class that includes CRUD convenience methods.
    """

    __abstract__ = True

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)
