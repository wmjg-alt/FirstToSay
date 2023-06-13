# First to Say
                                                                wmjg
### A webapp playing with document similarity
#### Say something original or be shamed as a copycat


    A docker-compose is included to allow you to deploy it all the same way I do.

    If you want to start fresh, you'll need to download some data from kaggle (sources in helper_funcs.py)

    Then, in command line run the command:

        | docker-compose up --build

Built Utilizing: 

* flask and sqlalchemy
* sqlite
* elasticsearch 
* spacy language detection
* nginx and gunicorn
* docker

Example of how it works:
---------------------------
                1. you register as a User so you can be the author
                2. input a sentence you think is original
                3. return your Quote and the most similar quotes in our db
                4. You either are original -> now your quote is part of the db
                    * Or you're not, and we show you who got there first
--------------------------
Under the hood:

                1. registered as an author in a sqlitedb
                2. normalize your input then spacy checks for grammaticality
                    * Using language detection, treshhold of recognition
                3. query elasticsearch for MOST similar quotes
                    * top elasticsearch results get cosin similarity scored
                4. below a certain similarity threshhold
                    * your Quote is generated as legitimate, entered into db
                    * else, show you who got there first
--------------------------
Every User (authors included) has an accessible profile page of all their quotes

And all Quote can be liked by a User

--------------------------
Future implementations:

    * Gamification: 3 strikes and you're out, track longest streak
    * "Followers": track who you're similar to, display in profile
    * Topic Model: display in profile your most common topics
    * cookies and tracking: can't see your entry result more than once; refresh or back loses that similarity results page
