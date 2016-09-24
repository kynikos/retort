# CgigC - Check the status of code repositories under a root directory.
# Copyright (C) 2016 Dario Giovannetti <dev@dariogiovannetti.net>
#
# This file is part of CgigC.
#
# CgigC is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CgigC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CgigC.  If not, see <http://www.gnu.org/licenses/>.

# The module must also support Python 2.6
# http://python-future.org/
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# TODO: Test builtins.super
# from builtins import super

# https://docs.python.org/2.6/library/internet.html
# https://docs.python.org/2.6/library/cgi.html
# http://www.tutorialspoint.com/python/python_cgi_programming.htm
import cgi
import sys
import os


class _Request(object):
    def __init__(self, keep_blank_form_values):
        """
        Store the HTTP request data, e.g. GET or POST data.
        """
        self.redirect_url = os.environ['REDIRECT_URL']

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


class _Response(object):
    DEFAULT_HEADERS = {'Status': '200 OK',
                       'Content-type': 'text/html'}

    def __init__(self):
        """
        Set up and send the HTTP response, headers and body.
        """
        self.set_headers(self.DEFAULT_HEADERS.copy())

    def set_headers(self, headers):
        # TODO: Use an OrderedDict?
        #       Is it allowed to have two headers with the same name?
        self.headers = headers

        # TODO: Implement get_headers(), update_headers()/add_headers(),
        #       remove_headers()

    @staticmethod
    def test():
        """
        Output cgi.test() and other information.

        Static method, it prints its own headers.
        """
        import platform

        # cgi.test() prints directly, including the headers, so it must come
        # first
        # TODO: Find a way to return the content instead of printing it
        #       directly, like any other response function
        cgi.test()

        # Note that from here on the content is normally returned
        html = '<h3>Python sys.version</h3>\n'
        html += '<div>{0}</div>\n'.format(sys.version)

        html += '<h3>PYTHONPATH:</h3>\n<ul>\n'
        for path in sys.path:
            html += "<li>{0}</li>\n".format(path)
        html += '</ul>\n'

        html += '<h3>Python platform.platform()</h3>\n'
        html += '<div>{0}</div>\n'.format(platform.platform())

        return html

    def _send(self, body):
        compiled_headers = '\n'.join(': '.join((name, value))
                                     for name, value in self.headers.items())
        print(compiled_headers, body, sep='\n\n', end='')


class CgigC(object):
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
            # TODO: Set a "500 Internal Server Error" status
            print('Content-type: text/plain\n')
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

    def __init__(self, keep_blank_form_values=False):
        """
        The main application.
        """
        # TODO: Implement logging for use in production
        # TODO: How to address HTTP errors and redirects?

        self.request = _Request(keep_blank_form_values)

    def route(self, url):
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
            self._serve(url, inner)
            return inner
        return decorator

    def serve(self, url, resource):
        """
        Test a set of urls in the given order and possibly immediately run the
        respective resource's 'make' function or method, or call the resource
        directly, then exit the program, thus preventing any following code,
        including the next rules, from being even tested.

        Designed to be used in projects that mostly construct the pages using
        Python code, relying on several functions, classes or modules.

        Example:

            class HelloWorld(object):
                def serve(self, app):
                    return 'Hello World!'


            app.serve(UrlExact('/hello_world.htm'), HelloWorld())
        """
        try:
            function = resource.make
        except AttributeError:
            function = resource
        self._serve(url, function)

    def _serve(self, url, function):
        testres = url.test(self)
        if testres:
            self.response = _Response()
            body = function(self, *url.args, **url.kwargs)
            self.response._send(body)
            # No need to test the remaining rules
            sys.exit(0)


class _UrlTest(object):
    def __init__(self):
        super(_UrlTest, self).__init__()
        self.args = ()
        self.kwargs = {}


class UrlDefault(_UrlTest):
    def test(self, app):
        return True


class UrlExact(_UrlTest):
    def __init__(self, url):
        super(UrlExact, self).__init__()
        self.url = url

    def test(self, app):
        return self.url == app.request.redirect_url
