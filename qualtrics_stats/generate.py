import xml.etree.ElementTree as ET
import requests
import csv
import json
import logging
from collections import defaultdict, Counter

from .running_average import RunningAverage


csv_override = None


class Question:
    pass


class MRQQuestion(Question):
    def __init__(self, question_xml, country_column):
        self.error = self._validate(question_xml)
        if self.error is not None:
            return

        self.general = RunningAverage()
        self.countries = defaultdict(RunningAverage)

        self.start, self.end = (int(c) for c in
                                question_xml.attrib['columns'].split('-', 1))
        self.title = question_xml.attrib['title']

        self.ignore = None
        if 'ignore_column' in question_xml.attrib:
            self.ignore = int(question_xml.attrib['ignore_column'])

        self.country_column = country_column

    def _validate(self, question_xml):
        if 'columns' not in question_xml.attrib:
            return 'mrq tag attribute "columns" missing'
        if 'title' not in question_xml.attrib:
            return 'mrq tag attribute "title" missing'

        if ('-' not in question_xml.attrib['columns'] or
            not all(s.isdigit()
                    for s in question_xml.attrib['columns'].split('-', 1))):
            return 'mrq tag attribute "columns" format should be NN-NN'
        if ('ignore_column' in question_xml.attrib and not question_xml.attrib['ignore_column'].isdigit()):
            return 'mrq tag attribute "ignore_column" should be a number'

    def __repr__(self):
        return "<MRQQuestion title='{}' start='{}' end='{}' avg='{}' count='{}'>".format(
            self.title, self.start, self.end, self.general.average, self.general.count)

    def parse_line(self, csv_line):
        # Skip unanswered question
        if csv_line[self.start] == '99999':
            return

        # Skip "I'm not sure" answer
        if self.ignore is not None and csv_line[self.ignore] != '0':
            return

        n = sum(1 for c in csv_line[self.start:self.end + 1] if c != '0')

        country = csv_line[self.country_column]
        self.general.add(n)
        if country != '99999':
            self.countries[country].add(n)

    def as_dict(self):
        return {
            'type': 'mrq',
            'title': self.title,
            'average': self.general.average,
            'countries': dict((k, v.average) for k, v in self.countries.items()),
            'max': self.end - self.start + 1,
            'min': 0
        }


class RankQuestion(Question):
    def __init__(self, question_xml, country_column):
        self.error = self._validate(question_xml)
        if self.error is not None:
            return

        self.general = Counter()
        self.countries = defaultdict(Counter)

        self.title = question_xml.attrib['title']
        self.columns = tuple(int(o.attrib['column']) for o in question_xml)
        self.answers = dict((int(o.attrib['column']), o.attrib['title'])
                            for o in question_xml)

        self.country_column = country_column

    def _validate(self, question_xml):
        if 'title' not in question_xml.attrib:
            return 'rank tag attribute "title" missing'

        if len(question_xml) < 2:
            return 'rank tag should have at least two option children'
        for o in question_xml:
            if 'title' not in o.attrib:
                return 'option tag attribute "title" missing'
            if 'column' not in o.attrib:
                return 'option tag attribute "column" missing'
            if not o.attrib['column'].isdigit():
                return 'option tag attribute "column" should be a number'

    def _get_top(self, counter):
        most_common = counter.most_common(1)
        if not most_common:
            return None
        return self.answers[most_common[0][0]]

    def __repr__(self):
        return "<RankQuestion title='{}' columns='{}' top='{}' count='{}'>".format(
            self.title, self.columns, self._get_top(self.general), sum(self.general.values()))

    def parse_line(self, csv_line):
        country = csv_line[self.country_column]
        for c in self.columns:
            if csv_line[c] == '1':
                self.general[c] += 1
                if country != '99999':
                    self.countries[country][c] += 1
                break
            elif csv_line[c] == '99999':
                # Skip unanswered rank
                return

    def as_dict(self):
        return {
            'type': 'rank',
            'title': self.title,
            'top': self._get_top(self.general),
            'countries': dict((k, self._get_top(v)) for k, v in self.countries.items())
        }


class SliderQuestion(Question):
    def __init__(self, question_xml, country_column):
        self.error = self._validate(question_xml)
        if self.error is not None:
            return

        self.general = RunningAverage()
        self.countries = defaultdict(RunningAverage)

        self.column = int(question_xml.attrib['column'])
        self.title = question_xml.attrib['title']

        self.country_column = country_column

        self.max, self.min = None, None
        if 'max' in question_xml.attrib:
            self.max = int(question_xml.attrib['max'])
        if 'min' in question_xml.attrib:
            self.min = int(question_xml.attrib['min'])

    def _validate(self, question_xml):
        if 'column' not in question_xml.attrib:
            return 'slider tag attribute "column" missing'
        if 'title' not in question_xml.attrib:
            return 'slider tag attribute "title" missing'

        if not question_xml.attrib['column'].isdigit():
            return 'slider tag attribute "column" should be a number'

        if 'max' in question_xml.attrib and not question_xml.attrib['max'].isdigit():
            return 'slider tag attribute "max" should be a number'
        if 'min' in question_xml.attrib and not question_xml.attrib['min'].isdigit():
            return 'slider tag attribute "min" should be a number'

    def __repr__(self):
        return "<SliderQuestion title='{}' column='{}' avg='{}' count='{}'>".format(
            self.title, self.column, self.general.average, self.general.count)

    def parse_line(self, csv_line):
        country = csv_line[self.country_column]
        if csv_line[self.column] != '99999':  # Skip unanswered sliders
            n = int(csv_line[self.column])
            self.general.add(n)
            if country != '99999':
                self.countries[country].add(n)

    def as_dict(self):
        return {
            'type': 'slider',
            'title': self.title,
            'average': self.general.average,
            'countries': dict((k, v.average) for k, v in self.countries.items()),
            'max': self.max if self.max is not None else self.general.max,
            'min': self.min if self.min is not None else self.general.min,
        }


class QualtricsStats():
    def __init__(self, survey_xml_spec):
        self.error = None

        try:
            tree = ET.parse(survey_xml_spec)
        except ET.ParseError as e:
            return self._report_error('XML parsing error: ' + str(e))

        validation_error = self._validate(tree)
        if validation_error is not None:
            return self._report_error(validation_error)

        self.user = tree.getroot().attrib['user']
        self.password = tree.getroot().attrib['password']

        survey_xml = tree.getroot().find('survey')
        self.survey_id = survey_xml.attrib['qualtrics_survey_id']
        cc = int(survey_xml.attrib['country_column'])

        self.questions = []
        for q in survey_xml:
            if q.tag == 'mrq':
                mrq = MRQQuestion(q, cc)
                if mrq.error is not None:
                    return self._report_error(mrq.error)
                self.questions.append(mrq)
            elif q.tag == 'rank':
                rank = RankQuestion(q, cc)
                if rank.error is not None:
                    return self._report_error(rank.error)
                self.questions.append(rank)
            elif q.tag == 'slider':
                slider = SliderQuestion(q, cc)
                if slider.error is not None:
                    return self._report_error(slider.error)
                self.questions.append(slider)

        logging.info('Loaded survey %s with %d questions',
                     self.survey_id, len(self.questions))

    def _report_error(self, error):
        logging.error(error)
        self.error = error

    def _validate(self, tree):
        if 'user' not in tree.getroot().attrib:
            return 'qualtrics tag attribute "user" missing'
        if 'password' not in tree.getroot().attrib:
            return 'qualtrics tag attribute "password" missing'

        survey_xml = tree.getroot().find('survey')
        if survey_xml is None:
            return 'survey tag missing'

        if 'qualtrics_survey_id' not in survey_xml.attrib:
            return 'survey tag attribute "qualtrics_survey_id" missing'
        if 'country_column' not in survey_xml.attrib:
            return 'survey tag attribute "country_column" missing'

    def _get(self):
        logging.info('Making Qualtrics API call...')

        url = 'https://new.qualtrics.com/Server/RestApi.php'
        data = {
            'Request': 'getResponseData',
            'User': self.user,
            'Password': self.password,
            'SurveyID': self.survey_id,
            'Format': 'CSV',
            'Labels': 1,
            'UnansweredRecode': 99999
        }
        r = requests.post(url, data=data, stream=True)
        csv_lines = r.iter_lines(decode_unicode=True)

        if csv_override:
            # For development and testing
            logging.info('Overriding csv source.')
            csv_lines = csv_override

        self.csv = csv.reader(csv_lines, strict=True)
        for i in range(2):
            next(self.csv)  # Strip title

    def run(self):
        if self.error:
            return json.dumps({'error': self.error})

        self._get()

        logging.info('Starting to fetch and parse data...')
        for csv_line in self.csv:
            for question in self.questions:
                question.parse_line(csv_line)

        return self._json()

    def _json(self):
        logging.info('Dumping results to JSON...')

        return json.dumps({
            'survey_qualtrics_id': self.survey_id,
            'statistics': [q.as_dict() for q in self.questions]
        }, indent=4)
