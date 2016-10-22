# Retort - Simple Python CGI framework.
# Copyright (C) 2016 Dario Giovannetti <dev@dariogiovannetti.net>
#
# This file is part of Retort.
#
# Retort is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Retort is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Retort.  If not, see <http://www.gnu.org/licenses/>.

# The module must also support Python 2.6
# http://python-future.org/
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# TODO: Test builtins.super
# from builtins import super

# https://docs.python.org/2/library/cookie.html
# https://pymotw.com/2/Cookie/
# http://jayconrod.com/posts/17/how-to-use-http-cookies-in-python
# https://en.wikipedia.org/wiki/HTTP_cookie#Cookie_attributes
from Cookie import SimpleCookie
from datetime import datetime, timedelta


class Cookie(SimpleCookie):
    def add(self, name, value, domain=None, path=None, expires=None,
            secure=True, httponly=True):
        self[name] = value
        if domain:
            self[name]['domain'] = domain
        if path:
            self[name]['path'] = path
        if expires:
            self.store_expires(name, expires)
        if secure:
            self[name]['secure'] = '1'
        if httponly:
            self[name]['httponly'] = '1'

    def store_expires(self, name, expires):
        self[name]['expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def expire(self, name):
        self.store_expires(name, datetime.utcnow() + timedelta(days=-1))
