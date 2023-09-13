"""
Test ability to ensure that tests can rely on other tests being executed first
and in the proper order

Output is tracked and an exception will be thrown if it does not match.
Run with the following command:

spektrum -s tests -p case_dependencies --select-tests "re:before.*","re:third.*","re:middle.*","re:fourth.*","re:after.*"

To verify order of test execution is determined by the order of their
definition, not by order of arguments, run with the following command:

spektrum -s tests -p case_dependencies --select-tests "re:after.*","re:fourth.*","re:middle.*","re:third.*","re:before.*"
""" # NOQA

from spektrum import Spec, DataSpec
from spektrum import depends_on, fixture


@fixture
class DependenciesFixture(Spec):
    async def before_all(self):
        await super().before_all()
        self.output = []

    async def after_all(self):
        expected_output = [
            'before',
            'first',
            'second',
            'third',
            'middle',
            'fourth',
            'after',
        ]
        if self.output != expected_output:
            raise Exception('output does not match')
        await super().after_all()


@fixture
class DependenciesDatasetFixture(DataSpec):
    async def before_all(self):
        await super().before_all()
        self.output = []

    async def after_all(self):
        expected_output = [
            'before 1',
            'before 2',
            'first 1',
            'first 2',
            'second 1',
            'second 2',
            'third 1',
            'third 2',
            'middle 1',
            'middle 2',
            'fourth 1',
            'fourth 2',
            'after 1',
            'after 2',
        ]
        if self.output != expected_output:
            raise Exception('output does not match')
        await super().after_all()


class SpecTestOne(DependenciesFixture):
    def before(self):
        self.output.append('before')

    def first(self):
        self.output.append('first')

    @depends_on(first)
    def second(self):
        self.output.append('second')

    @depends_on(second)
    def third(self):
        self.output.append('third')

    def middle(self):
        self.output.append('middle')

    def fourth(self):
        self.output.append('fourth')

    def after(self):
        self.output.append('after')


class SpecTestTwo(Spec):
    class SpecChildOne(DependenciesFixture):
        def before(self):
            self.output.append('before')

        def first(self):
            self.output.append('first')

        @depends_on(first)
        def second(self):
            self.output.append('second')

        @depends_on(second)
        def third(self):
            self.output.append('third')

        def middle(self):
            self.output.append('middle')

        @depends_on(third)
        def fourth(self):
            self.output.append('fourth')

        def after(self):
            self.output.append('after')


@fixture
class SpecChildOneFixture(DependenciesFixture):
    def before(self):
        self.output.append('before')

    def first(self):
        self.output.append('first')

    @depends_on(first)
    def second(self):
        self.output.append('second')

    @depends_on(second)
    def third(self):
        self.output.append('third')

    def middle(self):
        self.output.append('middle')

    @depends_on(first)
    def fourth(self):
        self.output.append('fourth')

    def after(self):
        self.output.append('after')


class SpecTestThree(Spec):
    class SpecChildOne(SpecChildOneFixture):
        pass


class SpecTestFour(Spec):
    class SpecDatasetChildOne(DependenciesDatasetFixture):
        DATASET = {
            '1': {'sample': 1},
            '2': {'args': {'sample': 2}, 'meta': {'test': 'sample'}}
        }

        def before(self, sample):
            self.output.append(f'before {sample}')

        def first(self, sample):
            self.output.append(f'first {sample}')

        @depends_on(first)
        def second(self, sample):
            self.output.append(f'second {sample}')

        @depends_on(second)
        def third(self, sample):
            self.output.append(f'third {sample}')

        def middle(self, sample):
            self.output.append(f'middle {sample}')

        def fourth(self, sample):
            self.output.append(f'fourth {sample}')

        def after(self, sample):
            self.output.append(f'after {sample}')

        class SpecNestedChildOne(DependenciesFixture):
            def before(self):
                self.output.append('before')

            def first(self):
                self.output.append('first')

            @depends_on(first)
            def second(self):
                self.output.append('second')

            @depends_on(second)
            def third(self):
                self.output.append('third')

            def middle(self):
                self.output.append('middle')

            @depends_on(third)
            def fourth(self):
                self.output.append('fourth')

            def after(self):
                self.output.append('after')
