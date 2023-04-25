from .models import User, Quote

from elasticsearch.helpers import parallel_bulk
from nltk import sent_tokenize
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash

base_text_length = 256

def sent_normalize(s):
    if isinstance(s, int) or isinstance(s, float):
        print(s)
        s = str(s)
    return s[:base_text_length].upper().strip()

def author_normalize(a):
    if isinstance(a, int) or isinstance(a, float):
        print(a)
        a = str(a)
    if "," in a:
        a = a.split(',')[0] # drop , trailing
    a = " ".join(a.split())
    return a.lower().strip()

def write_fail(idx, sent, author, message):
    with open('fails.txt','a', encoding='utf8') as f:
        f.write(str(idx) +"\t"+ sent +"\t"+ author + message+"\n")

def author_key(author):
    author = author.replace(" ", "_")
    return author#"".join(author.split()).strip()

def make_author(author):    
    spaceless = author_key(author)
    email = spaceless+"@admin.com"
    pss = generate_password_hash(spaceless+"admin",method='sha256')
    return {'username':author, 'email':email, 'password':pss}

def quote_to_db(text, target_user, db):
    quote = Quote(text=text, author=target_user.id)
    db.session.add(quote)
    db.session.commit()
    return quote

def quote_to_es(quote,es, index_name):
    quote_doc = {
        "id": quote.id,
        "text": quote.text,
    }
    es.index(index=index_name, id=quote.id, body=quote_doc)

def save_a_quote(text:str, target_user:User, db, es=None, index_name='myindex'):
    quote = quote_to_db(text, target_user, db)
    if es:
        quote_to_es(quote,es, index_name)
    return quote

def bulk_process_quotes(db, es, index_name, ):
    print("elastic search bulk processing...")
    # Get the total number of documents in the Quote table
    total_docs = db.session.query(Quote).count()

    # Set the batch size
    batch_size = 10000

    # Set up the Elasticsearch query
    query = {
        "query": {
            "match_all": {}
        }
    }
    fail_list = []

    # Use the scroll API to iterate over the documents in batches
    for batch_start in range(0, total_docs, batch_size):
        batch_end = min(batch_start + batch_size, total_docs)
        quotes = Quote.query.slice(batch_start, batch_end).all()

        actions = []

        # Build a list of actions for bulk indexing
        for quote in quotes:
            action = {
                "_index": index_name,
                "_id": quote.id,
                "_source": {
                    "id": quote.id,
                    "text": quote.text
                }
            }
            actions.append(action)

        # Bulk index the documents in parallel
        for success, info in parallel_bulk(es, actions):
            if not success:
                fail_list.append(info)
                print(f"A document failed: {info}")
        
    print(len(fail_list),"Failures")


def injest_csv_to_dfs(list_of_files, db):
    df_qts = pd.concat([pd.read_csv(f, encoding='utf-8') for f in list_of_files])
    df_qts = df_qts.dropna(subset=['quote'])

    df_qts['quote'] = df_qts['quote'].apply(sent_normalize)
    df_qts['author'] = df_qts['author'].fillna('Unknown Author')
    df_qts['author'] = df_qts['author'].apply(author_normalize)
    
    df_qts = df_qts.drop_duplicates(subset=['quote'])
    df_qts = df_qts.sample(frac=1).reset_index(drop=True)

    df_users = pd.DataFrame([make_author(a) for a in df_qts.author.unique()])

    df_users.drop_duplicates(subset=['email'], keep='first', inplace=True, ignore_index=True)
    
    print("building users db", len(df_users))

    df_users.to_sql('user', con=db.engine, if_exists='append', index=False)
    db.session.commit()

    print('users done, building quotes db')
    df_qts = df_qts.drop(columns=[col for col in df_qts.columns if col not in ['author','quote']])
    df_qts = df_qts.rename(columns={'quote': 'text'})
    
    from .models import User, Quote, Like
    ucount = User.query.count()
    print(f"Number in USERS db:{ucount}")
    print("nan authors", df_qts['author'].isna().sum())
    author_id_map = {Q.username: Q.id for Q in User.query.all()}

    df_qts['author'] = df_qts['author'].map(author_id_map)
    print("nan author_ids", df_qts['author'].isna().sum())

    df_qts.to_sql('quote', con=db.engine, if_exists='append', index=False)
    db.session.commit()

    qcount = Quote.query.count()
    print(f"Number in QUOTES db:{qcount}")


def pre_fill_db(db,es,index_name):
    # https://www.kaggle.com/datasets/manann/quotes-500k
    # https://www.kaggle.com/datasets/iampunitkmryh/funny-quotes?resource=download
    # https://www.kaggle.com/datasets/faseehurrehman/popular-quotes
    injest_csv_to_dfs(['data/quotes.csv','data/quotes_funny.csv','data/Popular_Quotes.csv'], db)

    print("bulk processing db to es")
    bulk_process_quotes(db, es, index_name, )
