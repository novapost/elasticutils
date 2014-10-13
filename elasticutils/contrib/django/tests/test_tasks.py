import uuid

from nose.tools import eq_

from elasticutils.contrib.django import get_es
from elasticutils.contrib.django.tasks import index_objects, unindex_objects
from elasticutils.contrib.django.tests import (
    FakeDjangoMappingType, FakeDjangoWithUuidMappingType, FakeModel,
    reset_model_cache)
from elasticutils.contrib.django.estestcase import ESTestCase


class TestTasks(ESTestCase):
    @classmethod
    def get_es(cls):
        return get_es()

    def setUp(self):
        super(TestTasks, self).setUp()
        TestTasks.create_index(FakeDjangoMappingType.get_index())
        reset_model_cache()

    def tearDown(self):
        super(TestTasks, self).tearDown()
        TestTasks.cleanup_index(FakeDjangoMappingType.get_index())

    def test_tasks(self):
        documents = [
            {'id': 1, 'name': 'odin skullcrusher'},
            {'id': 2, 'name': 'heimdall kneebiter'},
            {'id': 3, 'name': 'erik rose'}
            ]

        for doc in documents:
            FakeModel(**doc)

        # Test index_objects task
        index_objects(FakeDjangoMappingType, [1, 2, 3])
        FakeDjangoMappingType.refresh_index()
        eq_(FakeDjangoMappingType.search().count(), 3)

        # Test unindex_objects task
        unindex_objects(FakeDjangoMappingType, [1, 2, 3])
        FakeDjangoMappingType.refresh_index()
        eq_(FakeDjangoMappingType.search().count(), 0)

    def test_tasks_kwargs(self):
        """Test chunk size, es, and index parameters affects bulk_index"""
        documents = [
            {'id': 1, 'name': 'odin skullcrusher'},
            {'id': 2, 'name': 'heimdall kneebiter'},
            {'id': 3, 'name': 'erik rose'}
        ]

        for doc in documents:
            FakeModel(**doc)

        class MockMappingType(FakeDjangoMappingType):
            bulk_index_count = 0
            index_kwarg = None
            es_kwarg = None

            @classmethod
            def bulk_index(cls, *args, **kwargs):
                cls.bulk_index_count += 1
                cls.index_kwarg = kwargs.get('index')
                cls.es_kwarg = kwargs.get('es')

        index_objects(MockMappingType, [1, 2, 3])
        eq_(MockMappingType.bulk_index_count, 1)

        MockMappingType.bulk_index_count = 0

        index_objects(MockMappingType, [1, 2, 3], chunk_size=2)
        eq_(MockMappingType.bulk_index_count, 2)

        MockMappingType.bulk_index_count = 0

        index_objects(MockMappingType, [1, 2, 3], chunk_size=1)
        eq_(MockMappingType.bulk_index_count, 3)

        # test index and es kwargs
        MockMappingType.index_kwarg = None
        MockMappingType.es_kwarg = None
        index_objects(MockMappingType, [1, 2, 3])
        eq_(MockMappingType.index_kwarg, None)
        eq_(MockMappingType.es_kwarg, None)

        index_objects(MockMappingType, [1, 2, 3], es='crazy_es', index='crazy_index')
        eq_(MockMappingType.index_kwarg, 'crazy_index')
        eq_(MockMappingType.es_kwarg, 'crazy_es')

    def test_tasks_with_custom_id_field(self):
        docs = [
            {'uuid': uuid.uuid4(), 'name': 'odin skullcrusher'},
            {'uuid': uuid.uuid4(), 'name': 'heimdall kneebiter'},
            {'uuid': uuid.uuid4(), 'name': 'erik rose'}
            ]

        for d in docs:
            FakeModel(id_field='uuid', **d)

        ids = [d['uuid'] for d in docs]

        # Test index_objects task
        index_objects(FakeDjangoWithUuidMappingType, ids)
        FakeDjangoWithUuidMappingType.refresh_index()
        # need some sleep ?
        from time import sleep; sleep(1)
        # nothing was indexed because a StandardError was catched silently,
        # may be explicit should be better.
        eq_(FakeDjangoWithUuidMappingType.search().count(), 0)

        # Test everything has been indexed
        index_objects(FakeDjangoWithUuidMappingType, ids, id_field='uuid')
        FakeDjangoWithUuidMappingType.refresh_index()
        eq_(FakeDjangoWithUuidMappingType.search().count(), 3)

        # Test unindex_objects task
        unindex_objects(FakeDjangoWithUuidMappingType, ids)
        FakeDjangoWithUuidMappingType.refresh_index()
        eq_(FakeDjangoWithUuidMappingType.search().count(), 0)
