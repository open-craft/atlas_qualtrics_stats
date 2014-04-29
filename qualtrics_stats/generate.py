import xml.etree.ElementTree as ET
import requests
import csv
import json
import logging
from collections import defaultdict, Counter

from .running_average import RunningAverage


class Question:
    pass


class MRQQuestion(Question):
    def __init__(self, question_xml, country_column):
        self.general = RunningAverage()
        self.countries = defaultdict(RunningAverage)

        self.start, self.end = (int(c) for c in
                                question_xml.attrib['columns'].split('-', 1))
        self.title = question_xml.attrib['title']

        self.country_column = country_column

    def __repr__(self):
        return "<MRQQuestion title='{}' start='{}' end='{}' avg='{}' count='{}'>".format(
            self.title, self.start, self.end, self.general.average, self.general.count)

    def parse_line(self, csv_line):
        # Skip unanswered question
        if csv_line[self.start] == '99999':
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
            'countries': dict((k, v.average) for k, v in self.countries.items())
        }


class RankQuestion(Question):
    def __init__(self, question_xml, country_column):
        self.general = Counter()
        self.countries = defaultdict(Counter)

        self.title = question_xml.attrib['title']
        self.columns = tuple(int(o.attrib['column']) for o in question_xml)
        self.answers = dict((int(o.attrib['column']), o.attrib['title'])
                            for o in question_xml)

        self.country_column = country_column

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
        self.general = RunningAverage()
        self.countries = defaultdict(RunningAverage)

        self.column = int(question_xml.attrib['column'])
        self.title = question_xml.attrib['title']

        self.country_column = country_column

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
            'countries': dict((k, v.average) for k, v in self.countries.items())
        }


class QualtricsStats():
    def __init__(self, survey_xml_spec, csv_override=None):
        self.csv_override = csv_override

        tree = ET.parse(survey_xml_spec)

        self.user = tree.getroot().attrib['user']
        self.password = tree.getroot().attrib['password']

        survey_xml = tree.getroot().find('survey')
        self.survey_id = survey_xml.attrib['qualtrics_survey_id']
        cc = int(survey_xml.attrib['country_column'])
        self.questions = tuple(
            MRQQuestion(q, cc) if q.tag == 'mrq' else
            RankQuestion(q, cc) if q.tag == 'rank' else
            SliderQuestion(q, cc) if q.tag == 'slider' else None
            for q in survey_xml
        )

        logging.info('Loaded survey %s with %d questions',
                     self.survey_id, len(self.questions))

    def get(self):
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

        if self.csv_override:
            # For development and testing
            logging.info('Overriding csv source.')
            csv_lines = self.csv_override

        self.csv = csv.reader(csv_lines, strict=True)
        for i in range(2):
            next(self.csv)  # Strip title

    def run(self):
        self.get()

        logging.info('Starting to fetch and parse data...')
        for csv_line in self.csv:
            for question in self.questions:
                question.parse_line(csv_line)

        return self.json()

    def json(self):
        logging.info('Dumping results to JSON...')

        return json.dumps({
            'survey_qualtrics_id': self.survey_id,
            'statistics': [q.as_dict() for q in self.questions]
        }, indent=4)
