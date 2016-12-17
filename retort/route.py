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


class Diversion(object):
    def __init__(self, alias, *args, **kwargs):
        self.alias = alias
        self.args = args
        self.kwargs = kwargs

    def serve(self, app):
        app.divert(self.alias, *self.args, **self.kwargs)


class Handler(object):
    def __init__(self, handler, session=None, response=None):
        self.handler = handler
        self.session = session
        self.response = response

    def serve(self, app, *args, **kwargs):
        try:
            function = self.handler.make
        except AttributeError:
            function = self.handler

        app.response = self.response or app._default_response
        app.response.post_init(app)

        # Store the response *before* storing the session, since the
        # session may need to set the response headers

        app.session = self.session or app._default_session
        app.session.process_request(app)

        body = function(app, *args, **kwargs)
        app.response.serve(body)


class _Route(Handler):
    def __init__(self, handler, session=None, response=None):
        super(_Route, self).__init__(handler, session=session,
                                     response=response)

    def attempt(self, app):
        self.serve_args = []
        self.serve_kwargs = {}
        testres = self.test(app)
        if testres:
            self.serve(app, *self.serve_args, **self.serve_kwargs)

    def test(self, app):
        raise NotImplementedError()


class RouteDefault(_Route):
    def test(self, app):
        return True


class RouteExact(_Route):
    def __init__(self, url, handler, session=None, response=None):
        super(RouteExact, self).__init__(handler, session=session,
                                         response=response)
        self.url = url

    def test(self, app):
        return self.url == app.request.redirect_url


class RouteRegex(_Route):
    def __init__(self, pattern, handler, flags=0, session=None, response=None):
        super(RouteRegex, self).__init__(handler, session=session,
                                         response=response)
        self.pattern = pattern
        self.flags = flags

    def test(self, app):
        import re
        match = re.match(self.pattern, app.request.redirect_url,
                         flags=self.flags)
        if match:
            self.serve_args.append(match)
            return True
        return False
