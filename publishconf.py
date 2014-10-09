#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

SITEURL = 'http://danielweitzenfeld.github.io/passtheroc'
RELATIVE_URLS = False

FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/%s.atom.xml'

DELETE_OUTPUT_DIRECTORY = True

# Following items are often useful when publishing

#DISQUS_SITENAME = ""
#GOOGLE_ANALYTICS = ""
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

DISPLAY_PAGES_ON_MENU = False
DISPLAY_CATEGORIES_ON_MENU = False
EXTRA_HEADER = open('_nb_header.html').read().decode('utf-8')
TWITTER_USER = 'weitzenfeld'
TWITTER_FOLLOW_BUTTON = True