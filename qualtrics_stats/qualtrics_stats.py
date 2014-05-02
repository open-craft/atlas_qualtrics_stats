# Imports ###########################################################

import logging
import uuid
import datetime

from lxml import etree
from StringIO import StringIO

from xblock.core import XBlock
from xblock.fields import Scope, String, DateTime
from xblock.fragment import Fragment

from .utils import load_resource, render_template, get_scenarios_from_path


# Globals ###########################################################

log = logging.getLogger(__name__)


# Classes ###########################################################

class QualtricsXBlock(XBlock):
    """
    An XBlock showing the results from a Qualtrics statistics server, cached.
    """

    server = String(help="The base URL of the box serving the statistics results",
                    default='http://localhost:8080', scope=Scope.content)
    json_result = String(help="The cached statistics results",
                         default='', scope=Scope.content)
    last_fetched = DateTime(help="The last time json_result was fetched from server",
                            default=datetime.datetime.fromtimestamp(0),
                            scope=Scope.content)
    url_name = String(help="Unique name of the current statistic sent to the server",
                      default='qualtrics-default', scope=Scope.content)
    xml_content = String(help="XML content", default='', scope=Scope.content)
    xml_spec = String(help="XML specification to send to the server",
                      default='', scope=Scope.content)

    def student_view(self, context=None):
        if not self.xml_content:
            return Fragment(u'Edit the block to start...')

        fragment = Fragment(render_template('templates/html/qualtrics.html', {
            'self': self
        }))

        return fragment

    def studio_view(self, context):
        """
        Editing view in Studio
        """
        fragment = Fragment()
        fragment.add_content(render_template('templates/html/qualtrics_edit.html', {
            'self': self,
            'xml_content': self.xml_content or self.default_xml_content,
        }))
        fragment.add_javascript(load_resource('public/js/qualtrics_edit.js'))
        fragment.add_css(load_resource('public/css/qualtrics_edit.css'))

        fragment.initialize_js('QualtricsEditXBlock')

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
            else:
                response = {
                    'result': 'error',
                    'message': 'missing qualtrics tag'
                }

        log.debug(u'Response from Studio: {}'.format(response))
        return response

    @property
    def default_xml_content(self):
        return render_template('templates/xml/qualtrics_stats_default.xml', {
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
        if self.url_name == 'qualtrics-default':
            return 'qualtrics-{}'.format(uuid.uuid4())
        else:
            return self.url_name

    @staticmethod
    def workbench_scenarios():
        """
        Scenarios displayed by the workbench. Load them from external (private) repository
        """
        return get_scenarios_from_path('templates/xml')

