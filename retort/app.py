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
import os
# https://docs.python.org/2.6/library/internet.html
# https://docs.python.org/2.6/library/cgi.html
# http://www.tutorialspoint.com/python/python_cgi_programming.htm
import cgi
# https://docs.python.org/2/library/cookie.html
# https://pymotw.com/2/Cookie/
# http://jayconrod.com/posts/17/how-to-use-http-cookies-in-python
# https://en.wikipedia.org/wiki/HTTP_cookie#Cookie_attributes
from Cookie import SimpleCookie

from .session import NullSession
from .response import Response


class _Request(object):
    def __init__(self, keep_blank_form_values):
        """
        Store the HTTP request data, e.g. GET or POST data.
        """
        self.redirect_url = os.environ['REDIRECT_URL']
        self.cookies = SimpleCookie(os.environ['HTTP_COOKIE'])

        # FieldStorage must be instantiated only once
        self.form = cgi.FieldStorage(
                keep_blank_values=keep_blank_form_values)

    def get_form(self):
        """
        TODO
        """
        # TODO: Write more specific methods
        html = '<ul>Form:'
        for name in self.form.keys():
            # TODO: See also the getfirst() and getlist() methods
            #       See the 'filename', 'file', 'type' and 'done' attributes
            #       for uploads
            #       Items can be either FieldStorage or MiniFieldStorage
            html += "<li><b>{0}</b>: {1}</li>".format(
                                            name, self.form.getvalue(name))
        html += '</ul>'
        return html


class Retort(object):
    DEFAULT_SESSION = NullSession
    DEFAULT_RESPONSE = Response

    @staticmethod
    def debug():
        """
        Display uncaught exceptions' tracebacks. This static method is supposed
        to be run as early as possible in the code, especially before
        instantiating this very class. It is insecure to use this method in
        production.
        """
        # TODO: Enable debugging if a special url or parameter is sent?
        #       Or maybe check if the parameter is there only inside
        #         'display_uncaught_exception'?
        #       Or maybe encrypt the traceback before sending it?
        # TODO: Implement logging for use in production

        def display_uncaught_exception(type_, value, traceback):
            import traceback as _m_traceback
            # Don't rely on the _Response class or any other code in this
            # module, we're trying to debug it after all
            print('''Status: 500 Internal Server Error
Content-type: text/plain
''')
            _m_traceback.print_exception(type_, value, traceback,
                                         file=sys.stdout)
            sys.exit(1)

        sys.excepthook = display_uncaught_exception

    # cgitb seems to give more trouble than help...
    # @staticmethod
    # def debug(display=False, logdir=None, context=5, format='html'):
    #     """
    #     Shortcut for cgitb.enable(). This static method is supposed to be
    #     run as early as possible in the code, especially before instantiating
    #     this very class.
    #     """
    #     # h_ttps://docs.python.org/2.6/library/cgitb.html
    #     import cgitb
    #     # TO_DO: Does cgitb rotate the log files, or do they have to be
    #     #       cleaned up explicitly?
    #     cgitb.enable(display=1 if display else 0, logdir=logdir,
    #                  context=context, format=format)

    def __init__(self, keep_blank_form_values=False, default_session=None,
                 default_response=None):
        """
        The main application.
        """
        # TODO: Implement logging for use in production
        # TODO: How to address HTTP errors and redirects?

        self.request = _Request(keep_blank_form_values)
        self._default_session = default_session or self.DEFAULT_SESSION()
        self._default_response = default_response or self.DEFAULT_RESPONSE()

    def route(self, url, session=None, response=None):
        """
        Decorator that tests the url and possibly immediately calls the
        function and exits the program, thus preventing any following code,
        including further routes, from being even tested.

        Designed to be used in projects that mostly rely on non-Python template
        files, such as Jinja, and only use short functions to set the templates
        up.

        Example:

            @app.route(UrlExact('/hello_world.htm'))
            def hello_world(app):
                return 'Hello World!'
        """
        def decorator(function):
            def inner(*args, **kwargs):
                return function(*args, **kwargs)
            self._serve(url, inner, session, response)
            return inner
        return decorator

    def serve(self, url, resource, session=None, response=None):
        """
        Test a set of urls in the given order and possibly immediately run the
        respective resource's 'make' function or method, or call the resource
        directly, then exit the program, thus preventing any following code,
        including the next rules, from being even tested.

        Designed to be used in projects that mostly construct the pages using
        Python code, relying on several functions, classes or modules.

        Example:

            class HelloWorld(object):
                def make(self, app):
                    return 'Hello World!'


            app.serve(UrlExact('/hello_world.htm'), HelloWorld())
        """
        try:
            function = resource.make
        except AttributeError:
            function = resource
        self._serve(url, function, session, response)

    def _serve(self, url, function, session, response):
        testres = url.test(self)
        if testres:
            self.response = response or self._default_response
            self.response.post_init(self)

            # Store the response *before* storing the session, since the
            # session may need to set the response headers

            self.session = session or self._default_session
            self.session.process_request(self)

            body = function(self, *url.args, **url.kwargs)
            self.response.send(body)

            # No need to test the remaining url rules
            sys.exit(0)
