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
# from builtins import super

# https://docs.python.org/2.6/library/internet.html
# https://docs.python.org/2.6/library/cgi.html
# http://www.tutorialspoint.com/python/python_cgi_programming.htm
import cgi
import os


def debug(display=False, logdir=None, context=5, format='html'):
    """
    Shortcut for cgitb.enable().
    """
    # https://docs.python.org/2.6/library/cgitb.html
    import cgitb
    # TODO: Does cgitb rotate the log files, or do they have to be
    #       cleaned up explicitly?
    cgitb.enable(display=1 if display else 0, logdir=logdir,
                 context=context, format=format)


class Request(object):
    def __init__(self, keep_blank_form_values=False):
        """
        Store the HTTP request data, e.g. GET or POST data.
        """
        # FieldStorage must be instantiated only once
        self.form = cgi.FieldStorage(
                keep_blank_values=keep_blank_form_values)

    def get_env(self):
        """
        TODO
        """
        # TODO: Write more specific methods
        html = '<ul>Environment:'
        for name, value in os.environ.items():
            html += "<li><b>{0}</b>: {1}</li>".format(name, value)
        html += '</ul>'
        return html

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


class Response(object):
    def __init__(self, header={'Content-type': 'text/html'}):
        """
        Set up the response HTTP header.
        """
        # The header will be consumed only once the first time that self.out()
        # is called
        self.header = '\n'.join(': '.join((name, value))
                                for name, value in header.items())

    @staticmethod
    def test():
        """
        Output cgi.test() and other information.

        Static method, doesn't need to instantiate CgigC.
        """
        import sys
        import platform

        # cgi.test() also prints the header, so it must come first
        cgi.test()

        html = '<h3>Python sys.version</h3>\n'
        html += '<div>{0}</div>\n'.format(sys.version)

        html += '<h3>PYTHONPATH:</h3>\n<ul>\n'
        for path in sys.path:
            html += "<li>{0}</li>\n".format(path)
        html += '</ul>\n'

        html += '<h3>Python platform.platform()</h3>\n'
        html += '<div>{0}</div>\n'.format(platform.platform())

        print(html)

    def out(self, content, end=''):
        """
        Output content, with the HTTP header if still needed.
        """
        if self.header:
            content = '\n\n'.join((self.header, content))
            self.header = None
        print(content, end=end)

    def outn(self, content):
        """
        Same as self.out(), but adding a line break at the end.
        """
        self.out(content, end='\n')
