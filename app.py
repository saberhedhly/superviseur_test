from flask import Flask
from config import Config
from routes import blueprints

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Enregistre tous les blueprints d'un coup
for bp in blueprints:
    app.register_blueprint(bp)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0',port=port)
