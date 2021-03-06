#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
import os

AUTHOR = u'Dan Weitzenfeld'
SITENAME = u'Pass the ROC'
SITEURL = ''

PATH = 'content'

TIMEZONE = 'America/New_York'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None


DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True


DEFAULT_DATE_FORMAT = '%b %d, %Y'


# STATIC_OUT_DIR requires pelican 3.3+.
STATIC_PATHS = ['images', 'figures', 'downloads', 'favicon.png']
CODE_DIR = 'downloads/code'
NOTEBOOK_DIR = 'downloads/notebooks'


path = os.path.curdir
THEME = '%s/pelican-octopress-theme' % path
PLUGIN_PATHS = ['%s/pelican-plugins' % path]

PLUGINS = ['summary', 'liquid_tags.img', 'liquid_tags.video',
           'liquid_tags.include_code', 'liquid_tags.notebook',
           'liquid_tags.literal']

DISPLAY_PAGES_ON_MENU = True
DISPLAY_CATEGORIES_ON_MENU = False
EXTRA_HEADER = open('_nb_header.html').read().decode('utf-8')
TWITTER_USER = 'weitzenfeld'
TWITTER_FOLLOW_BUTTON = True
TWITTER_TWEET_BUTTON = True

DIRECT_TEMPLATES = ('index', 'archives')

# Set the article URL.
ARTICLE_URL = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'
YEAR_ARCHIVE_SAVE_AS = 'posts/{date:%Y}/index.html'
MONTH_ARCHIVE_SAVE_AS = 'posts/{date:%Y}/{date:%b}/index.html'