#!/usr/bin/python

import json
import time

import oauth2 as oauth

from numeric_string_parser import NumericStringParser

POLL_INTERVAL=70  #In seconds
QUESTION_TEXT="What is "

#Initial setup
print "Welcome to Math Bot!\n"

print "Let's setup your API credentials:"
CONSUMER_KEY = raw_input("API key: ")
CONSUMER_SECRET = raw_input("API secret: ")

print ""

print "Let's setup your twitter account credentials:"
ACCOUNT_KEY = raw_input("Account key: ")
ACCOUNT_SECRET = raw_input("Account secret: ")

print ""

print "All set! Math Bot is ready to answer questions!\n"

def oauth_req(url, key, secret, http_method="GET", post_body=None,
        http_headers=None):

    consumer = oauth.Consumer(key=CONSUMER_KEY, secret=CONSUMER_SECRET)
    token = oauth.Token(key=key, secret=secret)
    client = oauth.Client(consumer, token)
 
    resp, content = client.request(
        url,
        method=http_method,
        body=post_body,
        headers=http_headers,
        force_auth_header=True
    )

    return content

def rateLimitStatus():
    status = oauth_req('https://api.twitter.com/1.1/application/rate_limit_status.json',
                ACCOUNT_KEY, ACCOUNT_SECRET)
    return json.loads(status)

def remainingMentionChecks():
    status = rateLimitStatus()
  
    timelineStatus = status["resources"]["statuses"]["/statuses/mentions_timeline"]
    remaining = int(timelineStatus['remaining'])
    return remaining

def lastMention():
    """
    Gets last tweet mentioning this user.

    @return: Tuple containing tweet's tweet and sending user's screen name.
    """
    #Check rate limit
    checksRemaining = remainingMentionChecks()
    if not checksRemaining: 
        print "Cannot get mentions (rate limit)"
        return None
    #print "(Have %s checks remaining)." % str(checksRemaining)

    #Get timeline
    tweet = oauth_req('https://api.twitter.com/1.1/statuses/mentions_timeline.json',
                ACCOUNT_KEY, ACCOUNT_SECRET)
    jsonTweet = json.loads(tweet)

    #Check if request returned errors
    if isinstance(jsonTweet, dict):
        if "errors" in jsonTweet.keys():
            for error in jsonTweet["errors"]:
                print error["message"]
            return None
    
    #Verify at least one tweet returned
    numTweets = len(jsonTweet)
    if not numTweets:
        return None

    #Return latest tweet
    latestTweet = jsonTweet[0]

    text = latestTweet['text']
    sendingUser = latestTweet['user']['screen_name']
    return (text, sendingUser)

def lastProblem():
    """
    Returns latest problem sent to user in mention tweet 
    as well as the sending user's screen name.

    @return: Latest problem sent to user in mention tweet
    as well as the sending user's screen name.
    """
    print "Checking for messages (%s)" % time.ctime()
    
    (latestTweet, sendingUser) = lastMention()

    if not latestTweet:
        return None

    questionStart = latestTweet.find(QUESTION_TEXT)
    if questionStart != -1:
        questionEnd = latestTweet.find("?")
        if questionEnd != -1:
            problem = latestTweet[questionStart + len(QUESTION_TEXT): questionEnd]
            return (problem, sendingUser)
        problem = latestTweet[questionStart + len(QUESTION_TEXT):]
        return (problem, sendingUser)
    return None

def solveProblem(problem):
    """
    Solves a simple arithmetic problem.

    @param problem:     Simple math problem (e.g. "3^4 + 9")

    @return:            Solution (as string)
    """
    nsp = NumericStringParser()

    solution = ""
    try:
        solution = nsp.eval(problem)
    except:
        print "    -> Failed to solve: %s" % problem
        return None

    print "    -> Solution: ", solution
    return solution

def postTweet(key, secret, status, recipient=None):
    """
    Posts given tweet, optionally mentioning screen name
    of other user.

    @param key:     User key.
    @param secret:  User secret
    @param status:  Status to post.

    @keyword recipient: (Optional) Username to include in tweet as mention.

    @return:    Response (as json object) if successful,
                None otherwise.
    """
    body = ""
    if recipient:
        body = "status=@%s %s" % (recipient, status) 
    else:
        body = "status=%s" % status 

    response = oauth_req( 'https://api.twitter.com/1.1/statuses/update.json', 
        key, secret, 
        http_method="POST", post_body = body )

    jsonResponse = json.loads(response)
    if isinstance(jsonResponse, dict):
        if "errors" in jsonResponse.keys():
            if recipient:
                print "    -> Failed to send message '%s' to %s." % \
                    (status, recipient)
            else:
                print "    -> Failed to post status '%s'" % status
            for error in jsonResponse["errors"]:
                print "       Error: %s" % error["message"] 
            return None

    print "    -> Response sent!"

    return json.loads(response)

#Polls for tweets. Responds if math question appears.
previous = None
while True:
    #Get latest problem
    response = lastProblem()
   
    problem = sendingUser = None
    if response:
        problem = response[0]
        sendingUser = response[1]
    
    #If problem is new
    if problem and problem != previous:
        print "Received problem '%s' from %s" % (problem, sendingUser) 
        previous = problem 
    
        #Solve
        solution = solveProblem(problem)

        #Form response
        response = ""
        if not solution:
            response = "I'm stumped!" 
        else:
            response = "Easy! It's %s." % solution  

        #Tweet back
        postTweet(ACCOUNT_KEY, ACCOUNT_SECRET, response, sendingUser)

    #Sleep
    time.sleep(POLL_INTERVAL)

