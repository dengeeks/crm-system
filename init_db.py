from Server import db, application

with application.app_context():
    db.create_all()
    print("Tables created successfully")
