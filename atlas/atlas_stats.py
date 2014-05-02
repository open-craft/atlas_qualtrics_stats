# Imports ###########################################################

import logging
import uuid
import datetime
import requests
import pytz

from lxml import etree
from StringIO import StringIO

from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime
from xblock.fragment import Fragment

from .utils import render_template, get_scenarios_from_path


# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

class AtlasXBlock(XBlock):
    """
    An XBlock showing the results from a external statistics server, cached.
    """

    server = String(help="The base URL of the box serving the statistics results",
                    default='http://localhost:8080', scope=Scope.content)
    API_key = String(help="The API_key generated on the server",
                     default='', scope=Scope.content)
    json_result = String(help="The cached statistics results",
                         default='', scope=Scope.user_state_summary)
    last_fetched = DateTime(help="The last time json_result was fetched from server",
                            default=datetime.datetime.fromtimestamp(0),
                            scope=Scope.user_state_summary)
    url_name = String(help="Unique name of the current statistic sent to the server",
                      default='atlas-default', scope=Scope.content)
    xml_content = String(help="XML content", default='', scope=Scope.content)
    xml_spec = String(help="XML specification to send to the server",
                      default='', scope=Scope.content)

    def student_view(self, context=None):
        if not self.xml_content:
            return Fragment(u'Edit the block to start...')

        self._get_result()

        fragment = Fragment(render_template('templates/html/atlas.html', {
            'self': self
        }))

        return fragment

    def studio_view(self, context):
        """
        Editing view in Studio
        """
        fragment = Fragment()
        fragment.add_content(render_template('templates/html/atlas_edit.html', {
            'self': self,
            'xml_content': self.xml_content or self.default_xml_content,
        }))
        fragment.add_javascript(self.runtime.local_resource_url(
            'public/js/atlas_edit.js'))
        fragment.add_css(self.runtime.local_resource_url(
            'public/css/atlas_edit.css'))

        fragment.initialize_js('AtlasEditXBlock')

        return fragment

    @XBlock.json_handler
    def studio_submit(self, submissions, suffix=''):
        log.info(u'Received studio submissions: {}'.format(submissions))

        xml_content = submissions['xml_content']
        try:
            root = etree.parse(StringIO(xml_content)).getroot()
            q = root.find('qualtrics')
        except etree.XMLSyntaxError as e:
            response = {
                'result': 'error',
                'message': e.message
            }
        else:
            if q:
                response = {
                    'result': 'success',
                }
                self.xml_content = xml_content
                self.xml_spec = etree.tostring(q, encoding="utf8")
                for key in root.attrib:
                    setattr(self, key, root.attrib[key])

                self._put_spec()
            else:
                response = {
                    'result': 'error',
                    'message': 'missing qualtrics tag'
                }

        log.debug(u'Response from Studio: {}'.format(response))
        return response

    @property
    def _API_url(self):
        return '{}/stat/{}?API_key={}'.format(self.server, self.url_name,
                                              self.API_key)

    def _get_result(self):
        """
        Get the JSON results of the statistics run from the server if the
        cache is expired
        """
        if (not self.json_result or
                datetime.datetime.now(pytz.utc) - self.last_fetched
                < datetime.timedelta(minutes=10)):
            log.info('Fetching the results from the server')
            r = requests.get(self._API_url)
            if r.status_code == 200:
                self.json_result = r.text
                self.last_fetched = datetime.datetime.now(pytz.utc)

    def _put_spec(self):
        """
        Upload the XML spec to the processing server
        """
        log.info('Pushing the spec to the server')
        requests.put(self._API_url, data=self.xml_spec)

    @property
    def default_xml_content(self):
        return render_template('templates/xml/atlas_default.xml', {
            'self': self,
            'url_name': self.url_name_with_default,
        })

    @property
    def url_name_with_default(self):
        """
        Ensure the `url_name` is set to a unique, non-empty value.
        This should ideally be handled by Studio, but we need to declare the attribute
        to be able to use it from the workbench, and when this happen Studio doesn't set
        a unique default value - this property gives either the set value, or if none is set
        a randomized default value
        """
        if self.url_name == 'atlas-default':
            return 'atlas-{}'.format(uuid.uuid4())
        else:
            return self.url_name

    @staticmethod
    def workbench_scenarios():
        """
        Scenarios displayed by the workbench. Load them from external (private) repository
        """
        return get_scenarios_from_path('templates/xml')
