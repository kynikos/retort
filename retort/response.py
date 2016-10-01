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

import sys
import cgi
from collections import OrderedDict
from Cookie import SimpleCookie

from .data import http_status_codes


class Response(object):
    DEFAULT_STATUS = 200
    DEFAULT_CONTENT_TYPE = 'text/html'

    def __init__(self, status=DEFAULT_STATUS,
                 content_type=DEFAULT_CONTENT_TYPE):
        """
        Set up and send the HTTP response, headers and body.
        """
        # For performance, do only what's strictly necessary to configure
        # the object, and leave everything else to post_init, since
        # another response object may be used depending on the matched url,
        # so this would become useless
        self.status = status
        self.content_type = content_type

    def post_init(self, app):
        # In theory the order of headers shouldn't count, but it depends on the
        # clients, so be safe here and use OrderedDict
        # Note that some header names can be repeated, so the values of the
        # dictionary have to be tuples or lists, not simple strings
        # TODO: Implement generic set_header(), get_header(), add_header(),
        #       remove_header() ... methods to ensure that users enter tuples
        #       or lists as values, not simple strings
        self.headers = OrderedDict()
        # TODO: Allow setting default cookies or cookie parameters
        #       Especially set default 'Domain' and 'Path' attributes
        #       Also make it easy to set 'Expires' and 'Max-Age' attributes
        #       https://en.wikipedia.org/wiki/HTTP_cookie#Cookie_attributes
        # TODO: Write higher-level functions to manage sessions through cookies
        #       http://jayconrod.com/posts/17/how-to-use-http-cookies-in-python
        self.cookies = SimpleCookie()
        self.set_status(self.status)
        self.set_content_type(self.content_type)

    def set_status(self, code):
        self.status = code
        self.headers['Status'] = (http_status_codes[code], )

    def set_content_type(self, content_type):
        self.content_type = content_type
        self.headers['Content-type'] = (content_type, )

    def set_cookie(self, name, value, **attributes):
        self.cookies[name] = value
        for attr_name, attr_value in attributes.items():
            self.cookies[name][attr_name] = attr_value

    def _compile_headers(self):
        headers = []
        for name, values in self.headers.items():
            for value in values:
                headers.append(': '.join((name, value)))
        headers.append(self.cookies.output())
        # Maximize client compatibility with \r\n
        return '\r\n'.join(headers)

    def test(self):
        """
        Output cgi.test() and other information.
        """
        import platform

        # TODO: cgi.test() prints directly, including the headers, so it must
        #       come first; the normal headers have to be emptied; find a way
        #       to return the content of cgi.test() instead of printing it
        #       directly, like any other response function; note that the rest
        #       of the body is already normally returned
        self.headers.clear()
        cgi.test()

        html = '<h3>Python sys.version</h3>\n'
        html += '<div>{0}</div>\n'.format(sys.version)

        html += '<h3>PYTHONPATH:</h3>\n<ul>\n'
        for path in sys.path:
            html += "<li>{0}</li>\n".format(path)
        html += '</ul>\n'

        html += '<h3>Python platform.platform()</h3>\n'
        html += '<div>{0}</div>\n'.format(platform.platform())

        return html

    def send(self, body):
        # Maximize client compatibility with \r\n
        print(self._compile_headers(), body, sep='\r\n\r\n', end='')