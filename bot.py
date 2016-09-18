from datetime import datetime, timedelta
from os import path
from random import choice, randint
from time import sleep
import traceback
import sqlite3

import tweepy

import secret


SCRIPT_ROOT = path.dirname(path.realpath(__file__))

CORRECTION_PHRASES = [
    u'@{user} I think you mean "{correct_phrase}".',
    u'@{user} Actually, the correct phrase is "{correct_phrase}".',
    u'@{user} Perhaps you mean "{correct_phrase}".',
    u'@{user} Don\'t you mean "{correct_phrase}"?',
]


class Piqueachu(object):
    def main(self, dry_run=True):
        self.dry_run = dry_run

        self.pause_for_between(60*0, 60*4)
        self.authenticate_api()
        self.set_up_db()

        erroneous_tweets = self.get_recent_relevant_tweets(
            '"peaked my interest"'
        )
        for tweet in erroneous_tweets:
            self.pause_for_between(10, 20)
            self.correct(tweet)

        self.connection.close()

    def authenticate_api(self):
        auth = tweepy.OAuthHandler(secret.CONSUMER_KEY, secret.CONSUMER_SECRET)
        auth.set_access_token(secret.ACCESS_TOKEN, secret.ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(auth)

    def set_up_db(self):
        self.connection = sqlite3.connect(
            path.join(SCRIPT_ROOT, 'volume', 'history.db')
        )
        self.connection.isolation_level = None
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS users ('
            'id INTEGER PRIMARY KEY,'
            'screen_name TEXT'
            ')'
        )
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS tweets ('
            'id INTEGER PRIMARY KEY,'
            'time_replied INTEGER default (strftime(\'%s\', \'now\')),'
            'original_tweet TEXT,'
            'reply TEXT'
            ')'
        )

    def log(self, text):
        formatted_time = datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        log_text = u'[{}]: {}\n'.format(formatted_time, text)
        print(log_text.encode('utf8'))

    def save_user(self, user):
        self.cursor.execute(
            'INSERT INTO users (id, screen_name) VALUES (?, ?)',
            (user.id, user.screen_name)
        )
        self.log(
            'Added @{} to the contacted users'.format(user.screen_name)
        )

    def correct(self, tweet):
        # Log the user so that they never get corrected again
        self.save_user(tweet.user)

        correction_text = choice(CORRECTION_PHRASES).format(
            user=tweet.user.screen_name,
            correct_phrase='piqued my interest'
        )

        # Perform the correction
        if not self.dry_run:
            self.api.update_status(
                correction_text, in_reply_to_status_id=tweet.id
            )
            self.log('Successfully corrected tweet {}'.format(tweet.id))

        # Record the correction
        self.cursor.execute(
            'INSERT INTO tweets (id, original_tweet, reply) VALUES (?, ?, ?)',
            (tweet.id, tweet.text, correction_text)
        )
        self.log('Recorded tweet {} in the database'.format(tweet.id))

    def is_enlightened(self, text):
        return (
            'pique' in text or
            '"peaked my interest"' in text or 
            '\'peaked my interest\'' in text
        )

    def allow_tweet(self, tweet):
        # Don't reply to ancient tweets
        tweet_cutoff_time = datetime.utcnow() - timedelta(hours=24)
        if (tweet.created_at < tweet_cutoff_time):
            self.log('{} too old'.format(tweet.id))
            return False

        # Don't enlighten the enlightened
        if self.is_enlightened(tweet.text):
            self.log('{}: User already enlightened'.format(tweet.id))
            return False

        # Don't correct retweets or a conversation will get spammed
        if 'RT @' in tweet.text or hasattr(tweet, 'retweeted_status'):
            self.log('{}: Is a retweet'.format(tweet.id))
            return False

        # Never correct the same user more than once
        if self.cursor.execute(
            'SELECT id FROM users WHERE id=? LIMIT 1',
            (tweet.user.id,)
        ).fetchone():
            self.log('{}: User already contacted'.format(tweet.id))
            return False

        # Never correct the same tweet more than once
        if self.cursor.execute(
            'SELECT id FROM tweets WHERE id=? LIMIT 1',
            (tweet.id,)
        ).fetchone():
            self.log('{}: Already been tweeted'.format(tweet.id))
            return False

        return True

    def get_recent_relevant_tweets(self, search_query):
        search_args = {}

        # Get tweets after the most recent tweet
        query = self.cursor.execute(
            'SELECT id FROM tweets ORDER BY id DESC LIMIT 1'
        ).fetchone()
        if query:
            search_args['since_id'] = query[0]

        self.search_results = self.api.search(search_query, **search_args)
        self.log("Found {} possible tweets".format(len(self.search_results)))
        for tweet in self.search_results:
            self.log(u'{} - {}: "{}"'.format(
                tweet.id, tweet.user.name, tweet.text
            ))

        tweetable_results = list(filter(self.allow_tweet, self.search_results))
        self.log("Filtered down to {} tweets".format(len(tweetable_results)))
        for tweet in tweetable_results:
            self.log(u'{} - {}: "{}"'.format(
                tweet.id, tweet.user.name, tweet.text
            ))

        return tweetable_results

    def pause_for_between(self, start_bound, end_bound):
        interval = randint(start_bound, end_bound)
        print "Sleeping for {} seconds".format(interval)
        if self.dry_run:
            print "(Skipped because of dry run)"
        else:
            sleep(interval)


if __name__=='__main__':
    while True:
        try:
            Piqueachu().main(dry_run=False)
        except:
            traceback.print_exc()
            interval = randint(60*15, 60*20)
            print "Due to error, sleeping for extra {} seconds".format(interval)
        interval = randint(60*15, 60*20)
        print "Sleeping for {} seconds".format(interval)
        sleep(interval)
