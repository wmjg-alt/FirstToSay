from .models import User, Quote, Like
from elasticsearch.helpers import parallel_bulk
from werkzeug.security import generate_password_hash, check_password_hash
from spacy_langdetect import LanguageDetector

import pandas as pd
import difflib
import spacy

base_text_length = 256
accept_langs = ['en','fr','es','de','nl','da','nl', 'el','it', 'pt', 'ja','zh',] #western bias galore
fail_file = "data/fails.txt"

@spacy.Language.factory("language_detector")
def get_lang_detector(nlp, name):
   ''' helper for language detection w/ spacy'''
   return LanguageDetector()

nlp = spacy.load("en_core_web_sm")
nlp.add_pipe('language_detector', last=True)

def test_language(s:str):
    ''' spacy's detect_language is used to decide on how realistic a user_input is 
    Returns True when spacy confidently detects one of our accept_langs languages'''
    # decided on a spacy threshhold of 0.5 -- it detects gibberish as certain langs
    doc = nlp(s) 
    detect_language = doc._.language
    print(s, '\n', detect_language)
    return detect_language['score'] > 0.5 and detect_language['language'] in accept_langs


def sent_normalize(s:str):
    ''' normalize sentences to utf, uppercase, stripped; return '''
    if isinstance(s, int) or isinstance(s, float):
        print(s)
        s = str(s)
    s = s.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    return s[:base_text_length].upper().strip()

def author_normalize(a:str):
    ''' sets a standard for normalizing authors stripping and lowercasing
        dropping ,<title> format which was common in the data
    '''
    if isinstance(a, int) or isinstance(a, float):
        print(a)
        a = str(a)
    if "," in a:
        a = a.split(',')[0] # drop , trailing
    a = " ".join(a.split())
    return a.lower().strip()


def compare_texts(user_text: str, current_user: User, es):
    ''' Analyze a user_text against stored texts
        Query the ES index, then take results of that and rank
        sequence similarity; returning top similar texts
    '''
    es_hits = search_es(user_text, es)
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
            if text_ratio >= 0.7:
                #followers are for logging authors SIMILAR to you as someone you "follow"
                #future implementation, this was causing AppenderQuery ERror
                #other = User.query.filter_by(id=Q.author).first()
                #current_user.followers(other)
                pass   
        similarities.sort(key=lambda x: x.sim, reverse=True)
    
    return similarities[:5] if similarities else [], matched

def search_es(query_text:str, es):
    ''' build a search for elastic search es, from query_text
        using the analyzer; then search and return the top 10
    '''

    index_name = "myindex"
    search_body = {
        "query": {
            "match": {
                "text": {
                    "query": query_text,
                    "analyzer": "myanalyzer"
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
        "size": 10
    }
    res = es.search(index=index_name, body=search_body)
    return res['hits']['hits']

def gen_es_mapping(base_text_length:int):
    ''' builidng a predefinied es mapping, for building our search engine'''
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "integer"},
                "text": {"type": "text",}
            }
        },
        "settings":{
            "analysis": {
                "analyzer": {
                    "myanalyzer":{
                        "type": "standard",
                        "stopwords":"_english_",
                        "max_token_length": base_text_length,
                    }
                }
            }
        }
    }
    return mapping


def write_fail(idx, sent, author, message):
    ''' output the message that failed to be input into the db into a fails log file'''
    with open(fail_file,'a', encoding='utf8') as f:
        f.write(str(idx) +"\t"+ sent +"\t"+ author + message+"\n")

def author_key(author: str):
    ''' key author names up to remove spaces for creating an email  hadnle'''
    author = author.replace(" ", "_")
    return author#"".join(author.split()).strip()

def make_author(author: str):   
    ''' from the data, take an author name 
        generate an email and password for them
    ''' 
    spaceless = author_key(author)
    email = spaceless+"@admin.com"
    pss = generate_password_hash(spaceless+"admin",method='sha256')
    return {'username':author, 'email':email, 'password':pss}

def quote_to_db(text: str, target_user: User, db):
    ''' taking text and a user, add a Quote to Quotes, then commit that to db '''
    quote = Quote(text=text, author=target_user.id)
    db.session.add(quote)
    db.session.commit()
    return quote

def db_to_csv(db, ):
    ''' long term store the db in csv, for loss-less rebuild purposes '''
    pass

def quote_to_es(quote: Quote, es, index_name):
    ''' turn a quote into an object the ES can accept, then index it'''
    quote_doc = {
        "id": quote.id,
        "text": quote.text,
    }
    es.index(index=index_name, id=quote.id, body=quote_doc)

def save_a_quote(text:str, target_user:User, db, es=None, index_name:str='myindex'):
    ''' save a text/User input to the db (and ES if es) return the Quote'''
    quote = quote_to_db(text, target_user, db)
    if es:
        quote_to_es(quote,es, index_name)
    return quote

def bulk_process_quotes(db, es, index_name, ):
    ''' bulk process the quotes in the db into texts in the es 
        pre-filling the ES with DB data
    '''
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


def ingest_csv_to_dfs(list_of_files:list, db):
    ''' read in a series of csv files names with pandas, 
        normalize the fields of the csvs for quotes and authors
        bulk sql inject them into the db
    '''
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


def pre_fill_db(db, es, index_name:str):
    ''' fill the database with author users and quotes from 1/2 million quotes in data/
        ingest to db, then bulk process to es while logging failures in fail_file
    ''' 
    # https://www.kaggle.com/datasets/manann/quotes-500k
    # https://www.kaggle.com/datasets/iampunitkmryh/funny-quotes?resource=download
    # https://www.kaggle.com/datasets/faseehurrehman/popular-quotes
    # https://www.kaggle.com/datasets/abhishekvermasg1/goodreads-quotes
    try:
        import os
        os.remove(fail_file)
    except:
        pass
    
    ingest_csv_to_dfs(['data/quotes.csv','data/quotes_funny.csv','data/Popular_Quotes.csv', 'data/quotes2.csv'], db)
    print("bulk processing db to es")
    bulk_process_quotes(db, es, index_name, )
