"""
Test ability to ensure that tests can rely on other tests being executed first
and in the proper order

Output is tracked and an exception will be thrown if it does not match.
Run with the following command:

spektrum -s tests -p case_dependencies --select-tests "re:third.*","re:fourth.*"
"""

from spektrum import Spec, DataSpec
from spektrum import depends_on, fixture


@fixture
class DependenciesFixture(Spec):
    async def before_all(self):
        await super().before_all()
        self.output = []

    async def after_all(self):
        expected_output = [
            'first',
            'second',
            'third',
            'fourth',
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
            'first 1',
            'first 2',
            'second 1',
            'second 2',
            'third 1',
            'third 2',
            'fourth 1',
            'fourth 2',
        ]
        if self.output != expected_output:
            raise Exception('output does not match')
        await super().after_all()


class SpecTestOne(DependenciesFixture):
    def first(self):
        self.output.append('first')

    @depends_on(first)
    def second(self):
        self.output.append('second')

    @depends_on(second)
    def third(self):
        self.output.append('third')

    def fourth(self):
        self.output.append('fourth')


class SpecTestTwo(Spec):
    class SpecChildOne(DependenciesFixture):
        def first(self):
            self.output.append('first')

        @depends_on(first)
        def second(self):
            self.output.append('second')

        @depends_on(second)
        def third(self):
            self.output.append('third')

        @depends_on(third)
        def fourth(self):
            self.output.append('fourth')


@fixture
class SpecChildOneFixture(DependenciesFixture):
    def first(self):
        self.output.append('first')

    @depends_on(first)
    def second(self):
        self.output.append('second')

    @depends_on(second)
    def third(self):
        self.output.append('third')

    @depends_on(first)
    def fourth(self):
        self.output.append('fourth')


class SpecTestThree(Spec):
    class SpecChildOne(SpecChildOneFixture):
        pass


class SpecTestFour(Spec):
    class SpecDatasetChildOne(DependenciesDatasetFixture):
        DATASET = {
            '1': {'sample': 1},
            '2': {'args': {'sample': 2}, 'meta': {'test': 'sample'}}
        }

        def first(self, sample):
            self.output.append(f'first {sample}')

        @depends_on(first)
        def second(self, sample):
            self.output.append(f'second {sample}')

        @depends_on(second)
        def third(self, sample):
            self.output.append(f'third {sample}')

        def fourth(self, sample):
            self.output.append(f'fourth {sample}')

        class SpecNestedChildOne(DependenciesFixture):
            def first(self):
                self.output.append('first')

            @depends_on(first)
            def second(self):
                self.output.append('second')

            @depends_on(second)
            def third(self):
                self.output.append('third')

            @depends_on(third)
            def fourth(self):
                self.output.append('fourth')
