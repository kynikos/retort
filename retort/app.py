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
from functools import wraps
# https://docs.python.org/2.6/library/internet.html
# https://docs.python.org/2.6/library/cgi.html
# http://www.tutorialspoint.com/python/python_cgi_programming.htm
import cgi

from .cookie import Cookie
from .route import Diversion, Handler
from .session import NullSession
from .response import Response


class _Request(object):
    def __init__(self, keep_blank_form_values):
        """
        Store the HTTP request data, e.g. GET or POST data.
        """
        # TODO: Do something in case REDIRECT_URL is not defined?
        self.redirect_url = os.environ['REDIRECT_URL']
        self.cookies = Cookie(os.environ.get('HTTP_COOKIE', ''))

        # FieldStorage must be instantiated only once
        self.form = cgi.FieldStorage(
                keep_blank_values=keep_blank_form_values)


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

    def __init__(self, routes=[], handlers={}, keep_blank_form_values=False,
                 default_diversion=Diversion(404), default_session=None,
                 default_response=None, cache=None):
        """
        The main application.
        """
        # TODO: Implement logging for use in production

        self.routes = routes
        self.handlers = handlers
        self.request = _Request(keep_blank_form_values)
        self.default_diversion = default_diversion
        self.set_default_session(default_session or self.DEFAULT_SESSION())
        self.set_default_response(default_response or self.DEFAULT_RESPONSE())
        self.cache = cache

    def set_default_session(self, session):
        self._default_session = session

    def set_default_response(self, response):
        self._default_response = response

    def route(self, RouteClass, *route_args, **route_kwargs):
        """
        Route to the decorated function.

        Designed to be used in projects that mostly rely on non-Python template
        files, such as Jinja, and only use short functions to set the templates
        up.

        Example:

            @app.route(RouteExact, '/hello_world.htm')
            def hello_world(app):
                return 'Hello World!'
        """
        def decorator(function):
            @wraps(function)
            def inner(*args, **kwargs):
                return function(*args, **kwargs)
            lroute_args = list(route_args)
            lroute_args.append(inner)
            self.routes.append(RouteClass(*lroute_args, **route_kwargs))
            # TODO: Also register the routes in self.handlers; as an alias,
            #       maybe use the name of their function (as in Flask), or
            #       allow an optional 'alias' kwarg
            return inner
        return decorator

    def add_routes(self, *routes, **kwargs):
        """
        Route to the handler's 'make' function or method, or call the handler
        directly.

        Designed to be used in projects that mostly construct the pages using
        Python code, relying on several functions, classes or modules.

        Example:

            import hello_world_module

            def hello_world_function(app):
                return 'Hello World!'

            class HelloWorldClass(object):
                def make(self, app):
                    return 'Hello World!'

            app.add_routes(
                RouteExact('/hello_world_module.htm', hello_world_module),
                RouteExact('/hello_world_function.htm', hello_world_function),
                RouteExact('/hello_world_class.htm', HelloWorldClass()),
            )
        """
        # Python 2 must be supported, so the following definition can't be
        # used...
        # add_routes(self, *routes, default_diversion=None):
        default_diversion = kwargs.pop('default_diversion', None)

        self.routes.extend(routes)

        # TODO: Also register the routes in self.handlers; as an alias, maybe
        #       use the name of their function (as in Flask), or allow an
        #       optional 'alias' kwarg

        if default_diversion:
            # default_diversion can also be set in the constructor
            self.default_diversion = default_diversion

    def handler(self, alias, **handler_kwargs):
        def decorator(function):
            @wraps(function)
            def inner(*args, **kwargs):
                return function(*args, **kwargs)
            self.handlers[alias] = Handler(inner, **handler_kwargs)
            return inner
        return decorator

    def add_handlers(self, alias_to_handler):
        """
        Handlers are like routes, but they can only be called by divert(), i.e.
        they are not tested against any url.
        """
        self.handlers.update(alias_to_handler)

    def divert(self, alias, *args, **kwargs):
        self.handlers[alias].serve(self, *args, **kwargs)

    def redirect(self, url, status=302):
        def function(app):
            app.response.set_status(status)
            app.response.set_location(url)
            return ''
        Handler(function).serve(self)

    def run(self):
        for route in self.routes:
            # If a route responds, it will exit the appliction by default, so
            # no need to break here
            route.attempt(self)
        self.default_diversion.serve(self)
