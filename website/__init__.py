from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager
from elasticsearch import Elasticsearch

db = SQLAlchemy()
es = Elasticsearch(["http://localhost:9200/"])

DB_NAME = "database.db"
index_name = "myindex"


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "SOMEthingSECRETforME"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import User, Quote, Like

    create_database(app,db,es)

    # Test the connection to es by printing the cluster information
    mapping = es.indices.get_mapping(index=index_name)

    # Print the mapping
    print(mapping)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

def create_database(app,db,es):
    if not path.exists('instance/'+DB_NAME):
        with app.app_context():
            db.create_all()
            print("CREATED",DB_NAME,"DATABASE")
            metadata = db.MetaData()
            metadata.reflect(bind=db.engine)

            print("Tables in the database:")
            for table in metadata.tables:
                print(table)

        #if for some reason we've lost the database, rebuilt the index too
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "text"}
                }
            }
        }
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
        print("ES index "+ index_name + " recreated")
        es.indices.create(index=index_name, body=mapping)

        print("filling database with source quotes...")
        from website.helper_funcs import pre_fill_db
        with app.app_context():
            pre_fill_db(db,es,index_name)
    else:
        escount = es.cat.count(index=index_name, params={"format": "json"})[0]['count']
        with app.app_context():
            from .models import User, Quote, Like
            qcount = Quote.query.count()
        
        print(f"Number of documents in '{index_name}' index: {escount}\nNumber in QUOTES db:{qcount}")
        if int(escount) != int(qcount):
            from website.helper_funcs import bulk_process_quotes
            with app.app_context():
                bulk_process_quotes(db, es, index_name, )

