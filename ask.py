#!/usr/bin/env python


# ------------------------------------------------------------------------------- #
 # "THE SOUVLAKI-WARE LICENSE" (Revision 665.999):                               #
 # <drpaneas@gmail.com> wrote this file. As long as you retain this notice you   #
 # can do whatever you want with this stuff. If we meet some day, and you think  #
 # this stuff is worth it, you can buy me a souvlaki in return Panos Georgiadis  #
# ------------------------------------------------------------------------------- #


#############################################################
#							    #
# ask - instant AskUbuntu answers via terminal		    #
# written by Panos Georgiadis (drpaneas@gmail.com)	    #
# based on howdoi by Benjamin Gleitzman (gleitz@mit.edu)    #
#							    #
#############################################################

import argparse
import codecs
import glob
import os
import random
import re
import sys
import time


# utility functions from urrlib module
from urllib import quote as url_quote
from urllib import getproxies

# utility functions from pygments
try:
    from pygments import highlight
except ImportError:
    print 'Pygments is not installed... but dont worry I will do it for you right now!'
    time.sleep(3)
    os.system("sudo apt-get install python-pygments")

from pygments.lexers import guess_lexer, get_lexer_by_name
from pygments.formatters import TerminalFormatter
from pygments.util import ClassNotFound

# utility functions from pyquery module
try:
    from pyquery import PyQuery as pq
except ImportError:
    print 'PyQuery is not installed...but dont worry I will do it for you right now!'
    time.sleep(3)
    os.system("sudo apt-get install python-pyquery")

# utility functions from requests module
try:
    import requests
except ImportError:
    print 'python-requests is not installed...but dont worry I will do it for you right now!'
    time.sleep(3)
    os.system("sudo add-apt-repository ppa:chris-lea/python-requests -y")
    os.system("sudo apt-get update")
    os.system("sudo apt-get install python-requests")
    
from requests.exceptions import ConnectionError
from requests.exceptions import SSLError

# utility function from requests_cache
try:
    import requests_cache
except ImportError:
    print 'Python requests_cache is not installed...but dont worry I will do it for you right now!'
    time.sleep(3)
    os.system("git clone git://github.com/reclosedev/requests-cache.git")
    os.system("cd requests-cache")
    os.system("python setup.py install")



# Handle unicode (Python 2.x) for the ANSWER_HEADER
def u(x):
    return codecs.unicode_escape_decode(x)[0]


# fuck the https and use http instead
if os.getenv('ASK_DISABLE_SSL'): # Set http instead of https
    SEARCH_URL = 'http://www.google.com/search?q=site:askubuntu.com%20{0}'
else:
    SEARCH_URL = 'https://www.google.com/search?q=site:askubuntu.com%20{0}'

# Just a few to pick a random
USER_AGENTS = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:11.0) Gecko/20100101 Firefox/11.0',
               'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100 101 Firefox/22.0',
               'Mozilla/5.0 (Windows NT 6.1; rv:11.0) Gecko/20100101 Firefox/11.0',
               'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',
               'Mozilla/5.0 (Windows; Windows NT 6.1) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.46 Safari/536.5',)

# Set the Header (with the approriate unicode)
ANSWER_HEADER = u('--- Answer {0} ---\n{1}')
NO_ANSWER_MSG = '< No answer here >'

# Join /home/drpaneas/.ask
CACHE_DIR = os.path.join(os.path.expanduser('~'), '.ask')
CACHE_FILE = os.path.join(CACHE_DIR, 'cache{0}'.format(
        sys.version_info[0] if sys.version_info[0] == 3 else ''))

# Getting proxies
def get_proxies():
    proxies = getproxies()
    filtered_proxies = {}
    for key, value in proxies.items():
        if key.startswith('http'):
            if not value.startswith('http'):
                filtered_proxies[key] = 'http://%s' % value
            else:
                filtered_proxies[key] = value
    return filtered_proxies

# Fetch the HTML code from the webpage
def get_result(url):
    try:
        return requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, proxies=get_proxies()).text
    except requests.exceptions.SSLError as e:
        print('[ERROR] Encountered an SSL Error. Try using HTTP instead of '
              'HTTPS by setting the environment variable "ASK_DISABLE_SSL".\n')
        raise e

# Check if the links are valid (if the URL is identical AskUbuntu's pattern for questions)
def is_question(link):
    return re.search('questions/\d+/', link)

# Searching using Google, using the pattern 'site:askubuntu.com/ yourquerygoeshere'
def get_links(query):
    result = get_result(SEARCH_URL.format(url_quote(query)))
    html = pq(result)
    return [a.attrib['href'] for a in html('.l')] or \
        [a.attrib['href'] for a in html('.r')('a')]

# Fetches valid links (from AskUbuntu) and put them in order
def get_link_at_pos(links, position):
    links = [link for link in links if is_question(link)]

    if len(links) >= position:
        link = links[position-1]
    else:
        link = links[-1]
    return link

# Format output
def format_output(code, args):
    if not args['color']:
        return code
    lexer = None

    # try to find a lexer using the StackOverflow tags
    # or the query arguments
    for keyword in args['query'].split() + args['tags']:
        try:
            lexer = get_lexer_by_name(keyword)
            break
        except ClassNotFound:
            pass

    # no lexer found above, use the guesser
    if not lexer:
        lexer = guess_lexer(code)

    return highlight(code,
                     lexer,
                     TerminalFormatter(bg='dark'))


def get_answer(args, links):
    # Create the link
    # eg http://askubuntu.com/questions/267502/how-to-install-vlc-extensions-in-ubuntu
    link = get_link_at_pos(links, args['pos'])
    if args.get('link'):
        return link

    # Browse only at the votes tab (Add URL '?answertab=votes')
    # eg http://askubuntu.com/questions/267502/how-to-install-vlc-extensions-in-ubuntu?answertab=votes
    page = get_result(link + '?answertab=votes')

    # Get the HTML code of that page (including all the answers)
    html = pq(page)

    # From the votes tab, pick up the first (hopefully it's the top voted one)
    first_answer = html('.answer').eq(0)

    # Fetch the code (if any) by searching for code-tags
    instructions = first_answer.find('pre') or first_answer.find('code')

    # Finds Tags
    args['tags'] = [t.text for t in html('.post-tag')]

    if not instructions and not args['all']:
        text = first_answer.find('.post-text').eq(0).text()
    elif args['all']:
        texts = []
        for html_tag in first_answer.items('.post-text > *'):
            current_text = html_tag.text()
            if current_text:
                if html_tag[0].tag in ['pre', 'code']:
                    texts.append(format_output(current_text, args))
                else:
                    texts.append(current_text)
        texts.append('\n---\nAnswer from {0}'.format(link))
        text = '\n'.join(texts)
    else:
        text = format_output(instructions.eq(0).text(), args)
    if text is None:
        text = NO_ANSWER_MSG
    text = text.strip()
    return text


def get_instructions(args):
    # Creates a list containing all the valid AskUbuntu links
    links = get_links(args['query'])

    # In that case, blame Microsoft
    if not links:
        return ''
    answers = []

    # If the user wants only the first anwser, the append_header goes false
    append_header = args['num_answers'] > 1
    initial_position = args['pos']
    for answer_number in range(args['num_answers']):
        current_position = answer_number + initial_position
        args['pos'] = current_position
        answer = get_answer(args, links)
        if not answer:
            continue
        if append_header:
            answer = ANSWER_HEADER.format(current_position, answer)
        answer = answer + '\n'
        answers.append(answer)
    return '\n'.join(answers)


def enable_cache():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    requests_cache.install_cache(CACHE_FILE)


def clear_cache():
    for cache in glob.glob('{0}*'.format(CACHE_FILE)):
        os.remove(cache)


def ask(args):
    args['query'] = ' '.join(args['query']).replace('?', '')
    try:
        return get_instructions(args) or 'Sorry, couldn\'t find any answer for that topic\n'
    except (ConnectionError, SSLError):
        return 'Failed to establish network connection\n'


def get_parser():
    parser = argparse.ArgumentParser(description='instant AskUbuntu answers via the command line')
    parser.add_argument('query', metavar='QUERY', type=str, nargs='*',
                        help='the question to answer')
    parser.add_argument('-p','--pos', help='select answer in specified position (default: 1)', default=1, type=int)
    parser.add_argument('-a','--all', help='display the full text of the answer',
                        action='store_true')
    parser.add_argument('-l','--link', help='display only the answer link',
                        action='store_true')
    parser.add_argument('-c', '--color', help='enable colorized output',
                        action='store_true')
    parser.add_argument('-n','--num-answers', help='number of answers to return', default=1, type=int)
    parser.add_argument('-C','--clear-cache', help='clear the cache',
                        action='store_true')
    return parser


def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())

    if args['clear_cache']:
        clear_cache()
        print('Cache cleared successfully')
        return

    if not args['query']:
        parser.print_help()
        return

    # enable the cache if user doesn't want it to be disabled
    if not os.getenv('ASK_DISABLE_CACHE'):
        enable_cache()

    
    print(ask(args).encode('utf-8', 'ignore'))



if __name__ == '__main__':
    command_line_runner()

