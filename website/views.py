from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user

from .models import Quote, User, Like
from . import db, es, index_name
from .helper_funcs import save_a_quote, sent_normalize, test_language
from .helper_funcs import compare_texts, search_es
from string import printable, ascii_letters, digits, punctuation, whitespace

allowed_chars = set(ascii_letters + digits + punctuation + whitespace)


views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@views.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    ''' home view handling.
        POST requests get text analyzed for similarity to index
        GET requests display search home page
    '''
    if request.method == "POST":
        text = request.form.get('text')
        if not text:
            flash('Empty quotes not accepted',
                  category='error')
        else:
            # if text, normalize text
            text = sent_normalize(text)
            if not not (set(text) - allowed_chars):
                tmp = set(text) - allowed_chars
                flash("Can't handle some of those symbols: "+str(tmp),
                      category='error')
            elif not test_language(text):
                flash("spacy tells me you just posted cringe. a possibly ungrammatical sentence",
                      category='error')
            else:

                similar_texts, matched = compare_texts(text, current_user, es)
                print("MATCHES:", matched)

                if not matched:
                    quote = save_a_quote(text,
                                         current_user,
                                         db,
                                         es,
                                         index_name)
                    flash('Quote generated -- you were the first to say it',
                          category='success')
                    quote.sim = 1.0  # if newly generated
                    similar_texts = [quote] + similar_texts
                else:
                    flash('Matching quote already exists', category='error')

                return render_template("similar.html",
                                       user=current_user,
                                       posts=similar_texts,
                                       success=not matched,
                                       ran=True)

    return render_template("home.html", user=current_user)


@views.route('/profile/<username>')
@login_required
def profile(username):
    ''' profile display for user in url; pass that user's quotes'''
    target_user = User.query.filter_by(username=username).first()
    if not target_user:
        flash('no such user ' + username,
              category='error')
        return redirect(url_for("views.home"))
    else:
        quotes = target_user.quotes[::-1]
        return render_template("profile.html",
                               user=current_user,
                               posts=quotes,
                               poster=username)


@views.route("/like-quote/<quote_id>", methods=['POST'])
@login_required
def like(quote_id):
    ''' handle like functionality, done in static js file;
        backended here to store likes in user info
    '''
    quote = Quote.query.filter_by(id=quote_id).first()
    like = Like.query.filter_by(author=current_user.id,
                                quote_id=quote_id).first()
    if not quote:
        return jsonify({'error': 'Quote not exist'}, 400)
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, quote_id=quote_id)
        db.session.add(like)
        db.session.commit()
    
    return jsonify({'likes': len(quote.likes),
                    'liked': current_user.id in map(lambda x: x.author,
                                                    quote.likes)})
