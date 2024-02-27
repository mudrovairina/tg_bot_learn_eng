import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = sq.Column(sq.Integer, primary_key=True)
    id_user_tg = sq.Column(sq.Integer, unique=True)


class Vocabulary(Base):
    __tablename__ = 'vocabulary'
    id = sq.Column(sq.Integer, primary_key=True)
    ru_word = sq.Column(sq.Text, nullable=False)
    eng_word = sq.Column(sq.Text, nullable=False)


class PersonalDictionary(Base):
    __tablename__ = 'personal_dictionary'
    id = sq.Column(sq.Integer, primary_key=True)
    id_user = sq.Column(sq.Integer, sq.ForeignKey('user.id'), nullable=False)
    id_vocabulary = sq.Column(sq.Integer, sq.ForeignKey('vocabulary.id'), nullable=False)

    user = relationship(User, backref='personal_dictionaries')
    vocabulary = relationship(Vocabulary, backref='personal_dictionaries')


def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
