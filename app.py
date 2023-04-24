from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from nltk.tokenize import sent_tokenize
from datetime import datetime

import difflib
import time
import datetime

#https://huggingface.co/datasets/Abirate/english_quotes
#https://towardsdatascience.com/the-best-document-similarity-algorithm-in-2020-a-beginners-guide-a01b9ef8cf05

base_text_length = 1000
db_fpath = "db/quotes.db"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] =    'sqlite:///quotes.sqlite3'
app.config['SECRET_KEY'] =                 "RestInPieces"

db = SQLAlchemy(app)

class Quote(db.Model):
    id =            db.Column('quote_id', db.Integer, primary_key = True)
    text =          db.Column(db.String(base_text_length), unique=True)
    author =        db.Column(db.String(100))  
    date_added =    db.Column(db.DateTime, default=datetime.datetime.utcnow)


def quote_to_database(user_text, author):
    print(user_text)
    q = Quote(text=user_text, author=author)
    db.add(q)
    db.commit()


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_text = request.form.get('user_text')
        user_author = request.form.get('username')
        if user_text:
            user_text = user_text.upper()
            similar_texts, matched = compare_texts(user_text)
            print("MATCHES:", matched)

            if not matched:
                quote_to_database(user_text, user_author)

            return render_template('index.html', 
                                   results=similar_texts, 
                                   posted_text=user_text, 
                                   username=user_author, 
                                   matched=matched)
        else:
            return render_template('index.html', username=user_author)
    else:
        return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if " " in username:
            return render_template('index.html', username=username.upper())
        else:
            return render_template('index.html',error='first and last please')
    else:
        return render_template('index.html')


def compare_texts(user_text):
    database_texts = [(Q.text, Q.author, Q.date) for Q in Quote.query.all()]
    print(database_texts)

    similarities = []
    matched = False

    if len(database_texts) > 0:
        for database_text, database_author, entry_date in database_texts:
            text_ratio = difflib.SequenceMatcher(None, user_text, database_text).ratio()
            if text_ratio > 0.7:
                similarities.append((database_text, database_author, text_ratio, entry_date))
            if text_ratio >= 0.95 or matched:
                matched = True
        similarities.sort(key=lambda x: x[2], reverse=True)
    
    return similarities[:5] if similarities else [], matched


def wipe_db():
    db.session.query(Quote).delete()
    db.session.commit()


def pre_fill_db():
    import pandas as pd
    #https://www.kaggle.com/datasets/manann/quotes-500k
    # https://www.kaggle.com/datasets/iampunitkmryh/funny-quotes?resource=download
    #  https://www.kaggle.com/datasets/faseehurrehman/popular-quotes

    qt = pd.read_csv('data/quotes.csv', encoding='utf8')
    qts = pd.concat([pd.read_csv('data/quotes.csv', encoding='utf8'),
                     pd.read_csv('data/quotes_funny.csv', encoding='utf8')])
    
    database_texts = [Q.text for Q in Quote.query.all()]

    for index, row in qt.iterrows():
        print(index, len(database_texts), end='\r')
        text = str(row['quote']).upper().strip()
        author = str(row['author'])
        for sent in sent_tokenize(text):
            sent = sent.strip()[:base_text_length]
            if sent and len(sent) > 3 and len(sent.split()) > 1:
                if sent not in database_texts:
                    try:
                        quote_to_database(sent, author)
                        database_texts.append(sent)
                    except Exception as e:
                        print(e)
                        with open('fails.txt','a', encoding='utf8') as f:
                            f.write(str(index) +"\t"+ sent +"\t"+ author + str(e)[:100]+"\n")
                else:
                    print("REPEAT", sent)
                    with open('fails.txt','a', encoding='utf8') as f:
                        f.write(str(index) +"\t"+ sent +"\t"+ author +"\n")

if __name__ == "__main__":
    wipe_db()
    with app.app_context():
        db.create_all()
    pre_fill_db()
    app.run(debug=True)