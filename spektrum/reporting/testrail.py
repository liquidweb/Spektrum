from enum import Enum
from datetime import datetime

from spektrum import utils
from spektrum.reporting.data import CaseFormatData, SpecFormatData
from spektrum.reporting.transport import RetryTransport

import httpx

UNICODE_SKIP = u'\u2607'
UNICODE_SEP = u'\u221F'
UNICODE_ARROW = u'\u2192'
UNICODE_ARROW_BAR = u'\u219B'
UNICODE_CHECK = u'\u2713'
UNICODE_X = u'\u2717'


class TestRailStatus(Enum):
    PASSED = 1
    BLOCKED = 2
    UNTESTED = 3
    RETEST = 4
    FAILED = 5
    SKIPPED = 7


class TestRailRenderer(object):
    def __init__(self, reporting_options=None):
        self.reporting_options = reporting_options or {}
        self.enabled = False
        self.project = self.reporting_options.get('tr_project')
        self.suite = self.reporting_options.get('tr_suite')
        self.template = self.reporting_options.get('tr_template')
        self.run = self.reporting_options.get('tr_run')
        self.sections = {}
        self.specs = {}
        self.tr = TestRailClient(
            endpoint=self.reporting_options.get('tr_endpoint'),
            username=self.reporting_options.get('tr_username'),
            api_key=self.reporting_options.get('tr_apikey'),
        )

        if self.tr.username and self.tr.api_key:
            self.enabled = True
            self.sections = structure_testrail_dict(
                self.tr.get_sections(self.project, self.suite).json()
            )

    def reconcile_spec_and_section(self, spec, metadata, test_names, exclude, sections=None):
        utils.filter_cases_by_data(spec, metadata, test_names, exclude)

        spec_data = TestRailSpecData(spec)
        self._ensure_spec_hierarchy(spec_data, sections)
        self.specs[spec_data.id] = spec_data

        for child in spec_data.specs:
            self.reconcile_spec_and_section(
                child._spec,
                metadata,
                test_names,
                exclude,
                sections
            )

    def _ensure_spec_hierarchy(self, spec_data, sections=None):
        class_hierarchy = self._get_class_hierarchy(spec_data._spec)
        all_sections = self._get_all_sections()
        parent_id = None

        for i, class_name in enumerate(class_hierarchy):
            section_name = utils.camelcase_to_spaces(class_name)
            existing_section = self._find_existing_section(all_sections, section_name, parent_id)

            if existing_section:
                section_id = existing_section['id']
                suite_id = existing_section['suite_id']
            else:
                resp = self.tr.add_section(
                    self.project,
                    self.suite,
                    name=section_name,
                    description='',
                    parent_id=parent_id,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    section_id = result['id']
                    suite_id = result['suite_id']
                else:
                    return

            if i == len(class_hierarchy) - 1:
                spec_data.section_id = section_id
                spec_data.suite_id = suite_id

            parent_id = section_id

    def _get_class_hierarchy(self, spec):
        qualname = spec.__class__.__qualname__
        hierarchy = qualname.split('.')
        return hierarchy

    def _get_all_sections(self):
        try:
            response = self.tr.get_sections(self.project, self.suite)
            if response.status_code == 200:
                data = response.json()
                sections = data.get('sections', [])
                return sections
            else:
                return []
        except Exception:
            return []

    def _find_existing_section(self, all_sections, name, parent_id):
        for section in all_sections:
            section_name = section.get('name', '')
            section_parent_id = section.get('parent_id')

            if section_name == name:
                if parent_id == section_parent_id:
                    return section

        return None

    def track_top_level(self, specs, all_inherited, metadata, test_names, exclude):
        for spec in specs:
            self.reconcile_spec_and_section(
                spec,
                metadata,
                test_names,
                exclude,
                self.sections.values()
            )

    def start_reporting(self, dry_run):
        if dry_run:
            return

        if not self.run:
            time = datetime.now().strftime('%m/%d/%Y, %H:%M:%S%p')
            resp = self.tr.add_run(
                project_id=self.project,
                suite_id=self.suite,
                name=f'Spektrum {time}'
            )
            if resp.status_code == 200:
                self.run = resp.json()['id']

    def report_case(self, spec, case):
        case_data = TestRailCaseData(spec, case)
        if spec._id not in self.specs:
            return

        cached_spec = self.specs[spec._id]
        cached_case = next(
            (c for c in cached_spec.cases if c.raw_name == case.__name__),
            None
        )

        if cached_case and hasattr(cached_case, 'case_id'):
            case_data.case_id = cached_case.case_id
            case_data.section_id = cached_case.section_id
        else:
            case_data.case_id, case_data.section_id = self._create_case_on_demand(cached_spec, case)

            if not case_data.case_id:
                return

        status = TestRailStatus.FAILED
        if case_data.skipped:
            status = TestRailStatus.SKIPPED
        elif case_data.successful:
            status = TestRailStatus.PASSED

        timespan = int(case_data.elapsed_time) or 1

        lines = []
        mark = UNICODE_CHECK
        for expect in case_data.expects:
            mark = UNICODE_CHECK if expect.success else UNICODE_X
            arrow = UNICODE_ARROW_BAR if expect.required else UNICODE_ARROW

            lines.append(f'{arrow} {mark} {expect.evaluation}')

            if not expect.success:
                lines.append('    Values:')
                lines.append('    -------')
                lines.append(f'    | {expect.target_name}: {expect.target}')

                if str(expect.expected_name) != str(expect.expected):
                    lines.append(f'    | {expect.expected_name}: {expect.expected}')

        if case_data.errors:
            lines.append('')
            lines.append(utils.traceback_occurred_msg(case_data.error_type))
            lines.append('-' * 40)

            for error in case_data.errors:
                for line in error:
                    lines.append(line)

        if not self.run:
            return

        self.tr.add_result_for_case(
            run_id=self.run,
            case_id=case_data.case_id,
            status=status,
            elapsed=f'{timespan}s',
            comment='\n'.join(lines),
        )

    def report_spec(self, spec):
        pass

    def render(self, report):
        self.report = report

    def _create_case_on_demand(self, cached_spec, case):
        try:
            raw_case_name = case.__name__ if hasattr(case, '__name__') else str(case)
            if '_' in raw_case_name:
                case_name = utils.snakecase_to_spaces(raw_case_name)
            else:
                case_name = utils.camelcase_to_spaces(raw_case_name)

            tr_cases = self.tr.get_cases(self.project, cached_spec.suite_id, cached_spec.section_id)
            tr_case = next(
                (c for c in tr_cases if c['title'] == case_name),
                None
            )

            if tr_case:
                case_id = tr_case['id']
                section_id = tr_case['section_id']
            else:
                resp = self.tr.add_case(
                    cached_spec.section_id,
                    case_name,
                    template=self.template,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    case_id = result['id']
                    section_id = result['section_id']
                else:
                    return None, None

            class CachedCase:
                def __init__(self, case_id, section_id, raw_name, name):
                    self.case_id = case_id
                    self.section_id = section_id
                    self.raw_name = raw_name
                    self.name = name

            new_case = CachedCase(
                case_id=case_id,
                section_id=section_id,
                raw_name=raw_case_name,
                name=case_name
            )
            cached_spec.cases.append(new_case)

            return case_id, section_id

        except Exception:
            return None, None

    def get_cached_case_data(self, spec, raw_name):
        return next(
            (case for case in self.specs[spec._id].cases if case.raw_name == raw_name),
            None
        )


class TestRailCaseData(CaseFormatData):
    def __init__(self, spec, case):
        super().__init__(spec, case)
        self.case_id = None
        self.section_id = None


class TestRailSpecData(SpecFormatData):
    _case_format_cls = TestRailCaseData

    def __init__(self, spec):
        super().__init__(spec)
        self.section_id = None
        self.suite_id = None
        self.cases = []


class TestRailClient(object):
    def __init__(self, endpoint, username, api_key):
        self.endpoint = f'{endpoint}/index.php?'
        self.username = username
        self.api_key = api_key
        self._transport = RetryTransport(
            wrapped_transport=httpx.HTTPTransport(),
            max_attempts=5,
            backoff_factor=15
        )
        self._client = httpx.Client(transport=self._transport)

    def _get_paginated(self, item_collection, url=None, auth=None, params=None, timeout=None):
        resp = self._client.get(url, auth=auth, params=params, timeout=timeout)
        data = resp.json()
        offset = data.get('offset', 0)
        limit = data.get('limit', 150)
        items = data.get(item_collection, [])

        if data.get('_links', {}).get('next'):
            params.update({
                'offset': offset + limit,
                'limit': limit,
            })
            items.extend(
                self._get_paginated(item_collection, url=url, auth=auth, params=params)
            )

        return items

    def add_result_for_case(self, run_id, case_id, status, elapsed, comment):
        body = utils.clean_dictionary({
            'status_id': status.value,
            'elapsed': elapsed,
            'comment': comment,
        })

        return self._client.post(
            f'{self.endpoint}/api/v2/add_result_for_case/{run_id}/{case_id}',
            json=body,
            auth=(self.username, self.api_key),
            timeout=30,
        )

    def add_run(self, project_id, suite_id, name):
        body = utils.clean_dictionary({
            'suite_id': suite_id,
            'name': name,
        })

        return self._client.post(
            f'{self.endpoint}/api/v2/add_run/{project_id}',
            json=body,
            auth=(self.username, self.api_key),
            timeout=30,
        )

    def add_section(self, project_id, suite_id, name, description='', parent_id=None):
        body = utils.clean_dictionary({
            'suite_id': suite_id,
            'name': name,
            'description': description,
            'parent_id': parent_id,
        })

        return self._client.post(
            f'{self.endpoint}/api/v2/add_section/{project_id}',
            json=body,
            auth=(self.username, self.api_key),
            timeout=30,
        )

    def add_case(self, section_id, title, template=None, description=None):
        body = utils.clean_dictionary({
            'title': title,
            'template_id': template,
            'custom_description': description,
        })

        return self._client.post(
            f'{self.endpoint}/api/v2/add_case/{section_id}',
            json=body,
            auth=(self.username, self.api_key),
            timeout=30,
        )

    def update_case(self, case_id, **kwargs):
        body = utils.clean_dictionary(kwargs)

        return self._client.post(
            f'{self.endpoint}/api/v2/update_case/{case_id}',
            json=body,
            auth=(self.username, self.api_key),
            timeout=30
        )

    def get_sections(self, project_id, suite_id):
        return self._client.get(
            f'{self.endpoint}/api/v2/get_sections/{project_id}/&suite_id={suite_id}',
            auth=(self.username, self.api_key),
            timeout=30,
        )

    def get_cases(self, project_id, suite_id, section_id=None):
        parameters = {
            f'/api/v2/get_cases/{project_id}': None,
            'suite_id': suite_id,
            'limit': 100,
        }
        if section_id:
            parameters['section_id'] = section_id

        return self._get_paginated(
            'cases',
            url=f'{self.endpoint}',
            auth=(self.username, self.api_key),
            params=parameters,
            timeout=30
        )


def restructure(sections, level=0, structured=None):
    structured = structured or {}

    at_depth = {k: v for k, v in sections.items() if v['depth'] == level}

    for section_id, section in at_depth.items():
        parent_id = section['parent_id']

        if parent_id and parent_id not in structured:
            parent = sections[parent_id]
            structured[parent['id']] = parent

            if 'children' not in structured[parent['id']]:
                structured[parent['id']]['children'] = {}

            structured[parent_id]['children'][section_id] = section

        elif parent_id and parent_id in structured:
            structured[parent_id]['children'][section_id] = section

        elif parent_id is None and section_id not in structured:
            structured[section_id] = section
            structured[section_id]['children'] = {}

    return structured


def flatten_testrail_dict(data):
    return {section['id']: section for section in data.get('sections')}


def structure_testrail_dict(data):
    flattened = flatten_testrail_dict(data)
    depth_list = [v['depth'] for _, v in flattened.items()]
    max_depth = 1

    if len(depth_list) > 0:
        max_depth = max(depth_list)

    restructured = None
    for i in range(max_depth, -1, -1):
        restructured = restructure(flattened, i, restructured)

    return restructured
