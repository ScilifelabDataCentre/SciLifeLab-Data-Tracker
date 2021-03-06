"""Tests for dataset requests."""
import itertools
import uuid
import requests

# avoid pylint errors because of fixtures
# pylint: disable = redefined-outer-name, unused-import

from helpers import make_request, as_user, make_request_all_roles,\
    dataset_for_tests, USERS, random_string, parse_time, TEST_LABEL, mdb,\
    add_dataset, delete_dataset, USER_RE


def test_list_datasets(mdb):
    """
    Confirm that listing datasets work as intended.

    Tests:

      * Confirm all datasets in the database are listed.
      * Confirm that the correct fields are included
    """
    responses = make_request_all_roles('/api/v1/dataset/', ret_json=True)
    expected_fields = {'title', '_id', 'tags', 'properties'}
    for response in responses:
        assert response.code == 200
        assert len(response.data['datasets']) == mdb['datasets'].count_documents({})
        assert set(response.data['datasets'][0].keys()) == expected_fields


def test_list_user_datasets_permissions():
    """
    Confirm that users get the correct status code response.

    Tests:

      * Confirm that non-logged in users get 401, logged in users 200
    """
    responses = make_request_all_roles('/api/v1/dataset/user/')
    for response in responses:
        if response.role == 'no-login':
            assert response.code == 401
        else:
            assert response.code == 200


def test_list_user_datasets_with_datasets(mdb):
    """
    Confirm that users get the correct datasets.

    Tests:

      * Select a few users, confirm that the returned datasets are correct
      * Confirm that the included fields are the intended ones
    """
    session = requests.Session()
    orders = mdb['orders'].aggregate([{'$match': {'datasets': {'$not': {'$size': 0}}}},
                                      {'$sample': {'size': 2}}])
    user_uuids = list(itertools.chain.from_iterable(order['editors']
                                                    for order in orders))
    users = mdb['users'].find({'_id': {'$in': list(user_uuids)}})
    for user in users:
        user_orders = list(mdb['orders'].find({'editors': user['_id']},
                                              {'datasets': 1}))
        user_datasets = list(itertools.chain.from_iterable(order['datasets']
                                                           for order
                                                           in user_orders))
        user_datasets = [str(uuid) for uuid in user_datasets]

        as_user(session, user['auth_ids'][0])
        response = make_request(session, '/api/v1/dataset/user/')
        assert response.code == 200
        assert len(user_datasets) == len(response.data['datasets'])
        assert set(entry['_id'] for entry in response.data['datasets']) == set(user_datasets)


def test_list_user_datasets_no_datasets():
    """
    Confirm that users with no datasets get the correct response.

    Tests:

      * Select a few users, confirm that no datasets are returned as intended
    """
    # *::testers should have no datasets
    responses = make_request_all_roles('/api/v1/dataset/user/', ret_json=True)
    for response in responses:
        if response.role != 'no-login':
            assert len(response.data['datasets']) == 0


def test_random_dataset():
    """Request a random dataset."""
    responses = make_request_all_roles('/api/v1/dataset/random/', ret_json=True)
    for response in responses:
        assert response.code == 200
        assert len(response.data['datasets']) == 1


def test_random_datasets():
    """Request random datasets."""
    session = requests.Session()
    as_user(session, USERS['base'])
    for i in (1, 5, 0):
        response = make_request(session, f'/api/v1/dataset/random/{i}/')
        assert response.code == 200
        assert len(response.data['datasets']) == i

    response = make_request(session, '/api/v1/dataset/random/-1')
    assert response.code == 404
    assert not response.data


def test_get_dataset_get_permissions(mdb):
    """Test permissions for requesting a dataset."""
    orders = list(mdb['datasets'].aggregate([{'$sample': {'size': 2}}]))
    for order in orders:
        responses = make_request_all_roles(f'/api/v1/dataset/{order["_id"]}/', ret_json=True)
        for response in responses:
            assert response.data['dataset']
            assert response.code == 200


def test_get_dataset():
    """
    Request multiple datasets by uuid, one at a time.

    Datasets are choosen randomly using /api/v1/dataset/random.
    """
    session = requests.Session()
    for _ in range(10):
        orig = make_request(session, '/api/v1/dataset/random/')[0]['datasets'][0]
        response = make_request(session, f'/api/v1/dataset/{orig["_id"]}/')
        assert response[1] == 200
        requested = response[0]['dataset']
        assert orig == requested
        assert requested['_id'] not in requested['related']


def test_get_dataset_bad():
    """
    Request datasets using bad identifiers.

    All are expected to return 404.
    """
    session = requests.Session()
    for _ in range(5):
        response = make_request(session, f'/api/v1/dataset/{uuid.uuid4().hex}/')
        assert response.code == 404
        assert not response.data

    for _ in range(5):
        response = make_request(session, f'/api/v1/dataset/{random_string()}/')
        assert response.code == 404
        assert not response.data


def test_delete_dataset(mdb):
    """
    Add and delete datasets.

    * Check permissions.
    * Delete orders added by the add tests.
    * Confirm that related dataset entries in orders and projects are deleted.
    * Check that logs are created correctly.
    """
    session = requests.Session()

    uuids = [add_dataset() for _ in range(5)]

    datasets = list(mdb['datasets'].find(TEST_LABEL))
    if not datasets:
        assert False
    i = 0
    while i < len(datasets):
        for role in USERS:
            as_user(session, USERS[role])
            order = mdb['orders'].find_one({'datasets': datasets[i]['_id']})
            collections = list(mdb['collections'].find({'datasets': datasets[i]['_id']}))
            response = make_request(session,
                                    f'/api/v1/dataset/{datasets[i]["_id"]}/',
                                    method='DELETE')
            current_user = mdb['users'].find_one({'auth_ids': USERS[role]})
            if role == 'no-login':
                assert response.code == 401
                assert not response.data
            # only data managers or owners may delete datasets
            elif role in ('data', 'root') or current_user['_id'] in order['editors']:
                assert response.code == 200
                assert not response.data
                # confirm that dataset does not exist in mdb and that a log has been created
                assert not mdb['datasets'].find_one({'_id': datasets[i]['_id']})
                assert mdb['logs'].find_one({'data._id': datasets[i]['_id'],
                                             'action': 'delete',
                                             'data_type': 'dataset'})
                # confirm that no references to the dataset exist in orders or collection
                assert not list(mdb['orders'].find({'datasets': datasets[i]['_id']}))
                assert not list(mdb['collections'].find({'datasets': datasets[i]['_id']}))
                # confirm that the removal of the references are logged.
                assert mdb['logs'].find_one({'data._id': order['_id'],
                                             'action': 'edit',
                                             'data_type': 'order',
                                             'comment': f'Deleted dataset {datasets[i]["_id"]}'})
                p_log = list(mdb['logs'].find({'action': 'edit',
                                               'data_type': 'collection',
                                               'comment': f'Deleted dataset {datasets[i]["_id"]}'}))
                assert len(p_log) == len(collections)
                i += 1
                if i >= len(datasets):
                    break
            else:
                assert response.code == 403
                assert not response.data

    assert i > 0
    for uuid_group in uuids:
        delete_dataset(*uuid_group)


def test_delete_bad():
    """
    Bad deletion requests.

    Should require at least Steward.
    """
    session = requests.Session()
    as_user(session, USERS['data'])
    for _ in range(3):
        ds_uuid = random_string()
        response = make_request(session,
                                f'/api/v1/dataset/{ds_uuid}/',
                                method='DELETE')
        assert response.code == 404
        assert not response.data
        ds_uuid = uuid.uuid4().hex
        response = make_request(session,
                                f'/api/v1/dataset/{ds_uuid}/',
                                method='DELETE')
        assert response.code == 404
        assert not response.data


def test_dataset_update_permissions(dataset_for_tests):
    """
    Test the permissions for the request.

    Should require at least Steward or being the owner of the dataset.
    """
    ds_uuid = dataset_for_tests
    indata = {'title': 'Updated title'}
    responses = make_request_all_roles(f'/api/v1/dataset/{ds_uuid}/', method='PATCH', data=indata)
    for response in responses:
        if response.role in ('orders', 'data', 'root'):
            assert response.code == 200
        elif response.role == 'no-login':
            assert response.code == 401
        else:
            assert response.code == 403
        assert not response.data


def test_dataset_update_empty(dataset_for_tests):
    """
    Confirm response 400 to an empty update request

    Should require at least Steward or being the owner of the dataset.
    """
    ds_uuid = dataset_for_tests
    indata = {}
    responses = make_request_all_roles(f'/api/v1/dataset/{ds_uuid}/', method='PATCH', data=indata)
    for response in responses:
        if response.role in ('orders', 'data', 'root'):
            assert response.code == 200
        elif response.role == 'no-login':
            assert response.code == 401
        else:
            assert response.code == 403
        assert not response.data


def test_dataset_update(mdb, dataset_for_tests):
    """
    Update a dataset multiple times. Confirm that the update is done correctly.

    Should require at least Steward.
    """
    ds_uuid = dataset_for_tests
    indata = {'description': 'Test description - updated',
              'title': 'Test title - updated'}
    indata.update(TEST_LABEL)

    session = requests.Session()
    as_user(session, USERS['data'])

    response = make_request(session, f'/api/v1/dataset/{ds_uuid}/', method='PATCH', data=indata)
    assert response.code == 200
    assert not response.data

    dataset = mdb['datasets'].find_one({'_id': ds_uuid})
    for field in indata:
        assert dataset[field] == indata[field]
    assert mdb['logs'].find_one({'data._id': ds_uuid,
                                 'action': 'edit',
                                 'data_type': 'dataset'})


def test_dataset_update_bad(dataset_for_tests):
    """
    Confirm that bad requests will be rejected.

    Should require at least Steward.
    """
    for _ in range(2):
        indata = {'title': 'Updated title'}
        ds_uuid = random_string()
        responses = make_request_all_roles(f'/api/v1/dataset/{ds_uuid}/',
                                           method='PATCH', data=indata)
        for response in responses:
            if response.role in ('base', 'orders', 'data', 'root'):
                assert response.code == 404
            elif response.role == 'no-login':
                assert response.code == 401
            else:
                assert response.code == 404
                assert not response.data

        ds_uuid = uuid.uuid4().hex
        responses = make_request_all_roles(f'/api/v1/dataset/{ds_uuid}/',
                                           method='PATCH', data=indata)
        for response in responses:
            if response.role in ('base', 'orders', 'data', 'root'):
                assert response.code == 404
            elif response.role == 'no-login':
                assert response.code == 401
            else:
                assert response.code == 404
                assert not response.data

    ds_uuid = dataset_for_tests
    session = requests.Session()
    as_user(session, USERS['data'])
    indata = {'title': ''}
    response = make_request(session, f'/api/v1/dataset/{ds_uuid}/',
                            method='PATCH', data=indata)
    assert response.code == 400
    assert not response.data

    indata = {'extra': 'asd'}
    response = make_request(session, f'/api/v1/dataset/{ds_uuid}/',
                            method='PATCH', data=indata)
    assert response.code == 400
    assert not response.data

    indata = {'timestamp': 'asd'}
    response = make_request(session, f'/api/v1/dataset/{ds_uuid}/',
                            method='PATCH', data=indata)
    assert response.code == 400
    assert not response.data


def test_get_dataset_logs_permissions(mdb):
    """
    Get dataset logs.

    Assert that DATA_MANAGEMENT or user in editors is required.
    """
    dataset_data = mdb['datasets'].aggregate([{'$sample': {'size': 1}}]).next()
    order_data = mdb['orders'].find_one({'datasets': dataset_data['_id']})
    user_data = mdb['users'].find_one({'$or': [{'_id': {'$in': order_data['editors']}}]})
    responses = make_request_all_roles(f'/api/v1/dataset/{dataset_data["_id"]}/log/',
                                       ret_json=True)
    for response in responses:
        if response.role in ('data', 'root'):
            assert response.code == 200
            assert 'logs' in response.data
        elif response.role == 'no-login':
            assert response.code == 401
            assert not response.data
        else:
            assert response.code == 403
            assert not response.data

    session = requests.Session()

    as_user(session, user_data['auth_ids'][0])
    response = make_request(session,
                            f'/api/v1/dataset/{dataset_data["_id"]}/log/',
                            ret_json=True)

    assert response.code == 200
    assert 'logs' in response.data


def test_get_dataset_logs(mdb):
    """
    Request the logs for multiple datasets.

    Confirm that the logs contain only the intended fields.
    """
    session = requests.session()
    datasets = mdb['datasets'].aggregate([{'$sample': {'size': 2}}])
    for dataset in datasets:
        logs = list(mdb['logs'].find({'data_type': 'dataset', 'data._id': dataset['_id']}))
        as_user(session, USERS['data'])
        response = make_request(session, f'/api/v1/dataset/{dataset["_id"]}/log/', ret_json=True)
        assert response.data['dataType'] == 'dataset'
        assert response.data['entryId'] == str(dataset['_id'])
        assert len(response.data['logs']) == len(logs)
        assert response.code == 200


def test_add_dataset_permissions(mdb):
    """
    Add a dataset using .post(addDataset).

    Confirm that permissions are handled correctly.
    """
    session = requests.Session()

    db = mdb
    orders = db['orders'].aggregate([{'$sample': {'size': 2}}])
    for order in orders:
        indata = {'title': 'Test title',
                  'order': str(order['_id'])}
        indata.update(TEST_LABEL)

        responses = make_request_all_roles('/api/v1/dataset/',
                                           method='POST',
                                           data=indata,
                                           ret_json=True)
        for response in responses:
            if response.role in ('data', 'root'):
                assert response.code == 200
                assert '_id' in response.data
                assert len(response.data['_id']) == 36
            elif response.role == 'no-login':
                assert response.code == 401
                assert not response.data
            else:
                assert response.code == 403
                assert not response.data

        # as order editor
        owner = db['users'].find_one({'_id': order['editors'][0]})
        as_user(session, owner['auth_ids'][0])
        response = make_request(session,
                                '/api/v1/dataset/',
                                method='POST',
                                data=indata)
        assert response.code == 200
        assert '_id' in response.data
        assert len(response.data['_id']) == 36


def test_add_dataset(mdb):
    """
    Add a dataset using POST dataset.

    Set values in all available fields.
    """
    order = next(mdb['orders'].aggregate([{'$sample': {'size': 1}}]))
    indata = {'title': 'Test title',
              'description': 'Test description',
              'order': str(order['_id']),}
    indata.update(TEST_LABEL)

    session = requests.session()
    as_user(session, USERS['data'])

    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata,
                            ret_json=True)
    assert response.code == 200
    assert '_id' in response.data
    assert len(response.data['_id']) == 36
    indata.update({'_id': response.data['_id']})
    mdb_ds = mdb['datasets'].find_one({'_id': uuid.UUID(response.data['_id'])})
    mdb_o = mdb['orders'].find_one({'_id': order['_id']})
    mdb_ds['_id'] = str(mdb_ds['_id'])
    mdb_o['datasets'] = [str(ds_uuid) for ds_uuid in mdb_o['datasets']]
    for field in indata:
        if field == 'order':
            continue
        assert mdb_ds[field] == indata[field]
    assert response.data['_id'] in mdb_o['datasets']


def test_add_dataset_log(mdb):
    """
    Confirm that logs are added correctly when datasets are added.

    Check that both there is both update on order and add on dataset.
    """
    order = next(mdb['orders'].aggregate([{'$sample': {'size': 1}}]))
    indata = {'title': 'Test title',
              'order': str(order['_id'])}
    indata.update(TEST_LABEL)

    session = requests.session()
    as_user(session, USERS['data'])

    order_logs = list(mdb['logs'].find({'data_type': 'order', 'data._id': order['_id']}))

    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata,
                            ret_json=True)

    order_logs_post = list(mdb['logs'].find({'data_type': 'order', 'data._id': order['_id']}))
    print(order_logs_post)
    assert len(order_logs_post) == len(order_logs)+1
    ds_logs_post = list(mdb['logs'].find({'data_type': 'dataset',
                                         'data._id': uuid.UUID(response.data['_id'])}))
    assert len(ds_logs_post) == 1
    assert ds_logs_post[0]['action']


def test_add_dataset_bad_fields(mdb):
    """Attempt to add datasets with e.g. forbidden fields."""
    db = mdb
    order = next(db['orders'].aggregate([{'$sample': {'size': 1}}]))
    session = requests.Session()
    as_user(session, USERS['data'])

    indata = {'_id': 'asd',
              'title': 'test title',
              'order': str(order['_id']),}
    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata)
    assert response.code == 403
    assert not response.data

    indata = {'timestamp': 'asd',
              'title': 'test title'}
    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata)
    assert response.code == 400
    assert not response.data

    indata = {'extra': [{'asd': 123}],
              'title': 'test title'}
    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata)
    assert response.code == 400
    assert not response.data

    indata = {'links': [{'asd': 123}],
              'title': 'test title'}
    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata)
    assert response.code == 400
    assert not response.data

    indata = {'links': 'Some text',
              'title': 'test title'}
    response = make_request(session,
                            '/api/v1/dataset/',
                            method='POST',
                            data=indata)
    assert response.code == 400
    assert not response.data
