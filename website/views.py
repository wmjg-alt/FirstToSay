from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from .models import Quote, User, Like
from . import db, es, index_name
from .helper_funcs import save_a_quote, sent_normalize
import difflib

views = Blueprint('views',__name__)

def compare_texts(user_text):
    es_hits = search_es(user_text)
    print(es_hits)
    quote_ids = [hit['_source']['id'] for hit in es_hits]
    print(quote_ids)
    database_texts = [Q for Q in Quote.query.filter(Quote.id.in_(quote_ids)).all()]
    print(database_texts)

    similarities = []
    matched = False

    if len(database_texts) > 0:
        for Q in database_texts:
            text_ratio = difflib.SequenceMatcher(None, user_text, Q.text).ratio()
            if text_ratio > 0.2:
                Q.sim = text_ratio
                similarities.append(Q)
            if text_ratio >= 0.95 or matched:
                matched = True
        similarities.sort(key=lambda x: x.sim, reverse=True)
    
    return similarities[:5] if similarities else [], matched

def search_es(query_text):
    index_name = "myindex"
    search_body = {
        "query": {
            "match": {
                "text": {
                    "query": query_text,
                    "analyzer": "snowball"
                }
            }
        },
        "sort": [
            {
                "_score": {
                    "order": "desc"
                }
            },
            {
                "_id": {
                    "order": "asc"
                }
            }
        ],
        "size": 6
    }
    res = es.search(index=index_name, body=search_body)
    return res['hits']['hits']


@views.route('/', methods=['GET','POST'])
@views.route('/home', methods=['GET','POST'])
@login_required
def home():
    if request.method == "POST":
        text= request.form.get('text')
        
        if not text:
            flash('Empty quotes not accepted',category='error')
        else:
            text= sent_normalize(text)
            similar_texts, matched = compare_texts(text)
            print("MATCHES:", matched)

            if not matched:
                quote = save_a_quote(text, current_user, db, es, index_name)
                flash('Quote generated -- you were the first to say it', category='success')
                quote.sim = 1.0
                similar_texts = [quote] + similar_texts
            else:
                flash('Matching quote already exists', category='error')
            
            return render_template("similar.html", user=current_user, posts=similar_texts, success=not matched, ran=True)
    
    return render_template("home.html", user=current_user)


@views.route('/profile/<username>')
@login_required
def profile(username):
    target_user = User.query.filter_by(username=username).first()
    if not target_user:
        flash('no such user '+ username, category='error')
        return redirect(url_for("views.home"))
    else:
        quotes = target_user.quotes[::-1]
        return render_template("profile.html", user=current_user, posts=quotes, poster=username)


@views.route("/like-quote/<quote_id>", methods=['POST'])
@login_required
def like(quote_id):
    quote= Quote.query.filter_by(id=quote_id).first()
    like= Like.query.filter_by(author=current_user.id, quote_id=quote_id).first()
    if not quote:
        return jsonify({'error':'Quote not exist'}, 400)
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        like= Like(author=current_user.id, quote_id=quote_id)
        db.session.add(like)
        db.session.commit()
    
    return jsonify({'likes':len(quote.likes), 'liked':current_user.id in map(lambda x: x.author, quote.likes)})
